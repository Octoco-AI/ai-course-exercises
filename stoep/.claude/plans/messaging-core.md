# Plan: Messaging core (Stoep)

*Technical approach. Derived from `specs/messaging-core.md` and its Clarifications;
authored before any code.*

---

## Summary

Build a verified-human, server-readable messaging core on Firebase: Flutter client
(Riverpod) ↔ a Repository layer ↔ Firestore (message store + identity), Cloud
Functions for fan-out and push triggers, FCM for delivery acceleration, and Firebase
Phone Auth as the human-verification gate. Connections are invite-link/QR only.
Messages carry client-generated stable IDs for at-least-once + de-dup, server
timestamps for per-conversation ordering, and an offline outbox that shows "pending"
and auto-retries — the deliberate hook for the future mesh spec. No model, no AI in
this slice.

---

## Approach

- **Core technique**: deterministic event-sourced-ish messaging on Firestore.
  Client writes a message doc with a **client-generated ULID/UUID** as the doc ID
  (idempotent writes → at-least-once without duplicates); **server timestamp**
  (`FieldValue.serverTimestamp()`) is the ordering key within a conversation.
  Real-time delivery via Firestore **snapshot listeners**; FCM push is an
  accelerator for backgrounded apps, never the source of truth.
- **Offline outbox**: rely on Firestore's local persistence/offline write queue for
  the base case, wrapped in an explicit app-level **outbox** so the UI can render a
  true "pending" state and apply bounded retry/backoff. The outbox is the seam the
  future `bluetooth-mesh` spec plugs into.
- **Identity / human gate**: **Firebase Phone Auth (SMS OTP)** for human
  verification; an account is only "active" once OTP passes AND it has at least one
  **mutual accepted invite** (the invite-link/QR flow). No programmatic sending
  path exists.
- **State management**: **Riverpod** (Constitution says pick one — choosing Riverpod
  for its testability and the repository-provider fit). Repository pattern between
  UI and Firebase per Constitution.
- **No model / provider**: there is no LLM in this slice. Provider dependencies are
  the SMS-OTP backend (Firebase Auth) and FCM.
- **Why this over alternatives**: stays fully within the existing Constitution
  (Firestore as store, Functions for fan-out, no rule-bypassing logic). Rejected a
  custom websocket/relay backend (more infra, contradicts Firebase-first) and
  rejected E2E for this slice per the Phase-3 decision (server-readable keeps
  fan-out and the future API/MCP read-path viable).

---

## Data flow

1. User sends → client creates message doc with stable ID + `status: sending`,
   writes to the **local outbox** and to Firestore (offline-aware).
2. Firestore write commits → `serverTimestamp` assigned; doc lands in
   `conversations/{cid}/messages/{messageId}`.
3. **Cloud Function** `onMessageCreated` fans out: updates conversation summary
   (last message, unread counts) and triggers **FCM** to recipient devices.
4. Recipient's **snapshot listener** receives the message (or app foregrounds and
   syncs); client **de-dupes by message ID**, renders in `serverTimestamp` order,
   writes a delivery receipt → sender sees single→double tick.
5. All server-side steps log **PII-redacted** metadata only (message ID, conv ID,
   latency, status) — never the body or phone numbers.

```
sender ─▶ outbox ─▶ Firestore(messages) ─▶ CF:onMessageCreated ─▶ FCM ─▶ recipient device
   ▲          │            │                       │                          │
   │ pending  │ retry      └── serverTimestamp ─────┘                   snapshot listener
   └──────────┘                                                               │
        delivery receipt ◀────────────────────────────────────────────────────┘
                                  (redacted metrics/logs throughout)
```

---

## Integration points

- **Reads from**: `users` (verified identity, FCM tokens — no contact graph),
  `invites` (pending/accepted), `conversations/{cid}/messages`.
- **Writes to**: `conversations/{cid}/messages`, `conversations/{cid}` summary,
  `users/{uid}` (presence, fcm tokens), `invites`, `deliveryReceipts`.
- **Events emitted** (internal, redacted): `message.sent`, `message.delivered`,
  `verification.started|otp_passed|contact_matched|blocked`, `outbox.drained`.
- **External**: Firebase Phone Auth (SMS OTP), FCM. **No** LLM provider.
- **Security rules** (first-class, human sign-off — carried forward): only verified
  members of a conversation can read/write its messages; unverified accounts can do
  neither; no `allow read, write: if true`.

---

## Eval strategy

Every acceptance line in the spec maps to a monitor here.

- **Pre-deployment (every PR, against the Firebase emulator)**:
  - `test/reliability/soak_test` — 1,000-message soak: assert **zero loss, zero
    dup (post de-dup), zero out-of-order**. Blocks merge.
  - `test/auth/unverified_access_test` — auth eval set: assert **zero** send/receive
    from unverified accounts. Blocks merge.
  - `test/security/rules_test` — Firestore rules unit tests (emulator). Blocks merge.
  - `test/privacy/log_redaction_test` — scan emitted logs for bodies/phone numbers/
    PII: assert **zero**. Blocks merge.
  - `test/auth/false_reject_eval` — genuine-signup eval set: assert false-reject
    **< 1%**. Runs on PRs touching auth.
- **Canary / production**:
  - Send-to-delivered **p95 < 2s** (both online) — perf monitor on canary.
  - Offline→online: queued "pending" delivers **within 10s** of reconnect —
    reliability monitor.
  - Continuous drift alerts on delivery-fail rate, verification false-reject rate,
    outbox drain time (the silent-degradation guard).
- **Eval set growth**: false-reject and delivery-loss cases grow from real prod
  misses (per Constitution), not a frozen set.

---

## Rollout strategy

- **Pre-launch**: all blocking evals green on `main`; run the app against the
  **Firebase emulator** (Constitution: don't just trust CI green); smoke test with
  3 internal accounts.
- **Closed beta**: friends-and-family, invite-only (matches the spec's launch slice).
- **Canary → gradual**: small invite-only canary for 24h watching rollback triggers,
  then widen in steps with quality gates between.
- **Feature flag**: `messaging_core_enabled` (Remote Config), off by default,
  per-account override.
- **Rollback trigger (automatic)**: any hard-zero gate breached in prod (unverified
  access, message loss, PII-in-logs) OR send-to-delivered p95 > 2s sustained over a
  defined window. Windows finalised with the (carried-forward) sign-off owners.
- **Graceful degradation**: per spec — offline → pending outbox; FCM fail → listener
  sync; OTP provider degraded → retryable error, never a silent unverified account.

---

## Risks and mitigations

1. **Risk**: Firestore listener fan-out + read-receipt writes blow the p95 < 2s bar
   or run up cost at the 8-member group ceiling.
   **Mitigation**: denormalised conversation-summary doc; batch read receipts;
   load-test fan-out in the soak eval before widening rollout.

2. **Risk**: "at-least-once" produces visible duplicates if client de-dup is wrong.
   **Mitigation**: stable client-generated IDs as the doc ID makes writes idempotent
   at the store layer; de-dup is then a safety net, not the primary defence; covered
   by the soak test's zero-dup assertion.

3. **Risk**: human-verification gate either lets bots in (false negative) or blocks
   real people (false positive > 1%).
   **Mitigation**: require OTP **and** mutual accepted invite; per-number/per-device
   signup rate caps; behavioural flags (burst invite/send) → review queue; appeal
   path; track false-reject as a CE gate.

4. **Risk**: privacy leak — message body or phone number reaches logs/crash reports.
   **Mitigation**: structured logging with redaction by default; the
   `log_redaction_test` blocks merge; no body fields passed to analytics.

5. **Risk**: security rules drift to something over-broad during iteration.
   **Mitigation**: rules are code with emulator unit tests in CI; human sign-off
   required (carried-forward owner); explicit lint/review check for
   `allow ... : if true`.

6. **Risk**: the offline outbox diverges from Firestore's own offline queue and
   double-sends or strands messages.
   **Mitigation**: single source of truth = the message doc + its `status`; outbox
   is a view/retry-coordinator over it, not a second store; reconcile on reconnect
   by ID.

---

## Cost estimate

No LLM cost (no model). Costs are Firebase infra, driven by reads/writes/pushes.

- **Per message**: ~1 write + fan-out reads/writes + read-receipt write + 1 FCM push
  (FCM is free). Dominated by Firestore document operations.
- **Rough order**: at small friend-group scale this sits comfortably in low Firestore
  tiers; the cost lever is **read-receipt and presence write volume**, not messages
  themselves — hence batching (Risk 1). Firm numbers to be modelled once the schema
  is signed off.
- No prompt-caching / token cost applies.

---

## Open questions

Carried forward from Phase 3 (time-boxed; don't block starting):

- **Sign-off owner**: **Herman** owns Firestore security rules, the auth/verification
  flow, and the privacy posture sign-off (human-owned per Constitution). *Resolved.*
- **Media**: confirmed **out of scope** (future story). *Resolved.*
- **Delete-for-everyone window** — proposed ~1 hour; confirm.
- **Presence model** — show online/last-seen or not? (Privacy + write-cost
  implications; lean toward minimal presence for the MVP.)

---

## Out of scope (for the plan)

- UI visual design — product-owned; this plan covers the data/repository contract
  and states (pending/sent/delivered), not pixels.
- External API + MCP surface — separate spec/plan (`external-api-mcp`).
- Bluetooth mesh — separate spec/plan (`bluetooth-mesh`); only the outbox seam is
  prepared here.
- Opt-in AI smart replies — separate AI spec/plan.
