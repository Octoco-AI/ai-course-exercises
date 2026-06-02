# Tasks: Messaging core (Stoep)

*Actionable breakdown of `plans/messaging-core.md`. One task = one mergeable change,
~1–2 days. Ordered by dependency; unblocked tasks can start now.*

---

## Task conventions

- **Size**: each task is ~1–2 days. If larger, split.
- **Done-when**: each task has an explicit acceptance criterion — a passing test or a
  running deployment, not "works on my machine". Where a task maps to a spec
  acceptance gate, it's noted.
- **Dependencies**: `depends-on: #N`. Tasks with none are ready to start.
- **Owner**: filled in at sprint planning. Note: security rules, auth flow, and
  privacy posture are **Herman's** sign-off (per spec).

---

## 1. Project + Firebase emulator scaffold

**Description**: Flutter app skeleton with Riverpod wired; Firebase project config;
local **emulator suite** (Auth, Firestore, Functions) running. Repository-pattern
folder structure. No features yet.

**Done-when**: app builds on iOS + Android; `firebase emulators:start` runs Auth +
Firestore + Functions; a trivial repository read against the emulator passes in CI.

**Depends-on**: none. **Estimate**: 1 day.

---

## 2. Data model + Firestore security rules (first cut)

**Description**: define schema — `users`, `invites`, `conversations/{cid}`,
`conversations/{cid}/messages/{messageId}`, `deliveryReceipts`. Write security rules:
only verified members of a conversation read/write its messages; unverified accounts
can do neither; no `allow ... : if true`. Rules unit tests on the emulator.

**Done-when**: `test/security/rules_test` passes on the emulator and includes a case
proving an unverified / non-member account is denied. **Maps to spec gate: zero
unverified send/receive; security-rules sign-off (Herman).**

**Depends-on**: #1. **Estimate**: 2 days. *(Human sign-off required before merge.)*

---

## 3. Human-verification onboarding (SMS OTP + mutual invite)

**Description**: Firebase Phone Auth OTP flow; account becomes "active" only after
OTP passes AND one mutual accepted invite. Invite-link/QR generation + accept flow.
Per-number/per-device signup rate caps. No address-book upload, no number lookup.

**Done-when**: a new user can verify via OTP and connect only via an accepted invite;
integration test covers OTP-pass → invite-accept → active. **Maps to spec gates:
verified-human-only; carries the <1% false-reject target (measured in #9). Auth-flow
sign-off (Herman).**

**Depends-on**: #2. **Estimate**: 2 days.

---

## 4. Send + receive text (Firestore listeners, stable IDs, ordering)

**Description**: send path writes a message doc with **client-generated stable ID**
as doc ID and `serverTimestamp`; receive path via **snapshot listener**; client
**de-dupes by ID** and renders in server-timestamp order. Status model
sending→sent→delivered with delivery receipts.

**Done-when**: two emulator clients exchange messages in correct order with no
duplicates; unit tests for ID idempotency and ordering. **Maps to spec: at-least-once
+ per-chat ordering + client de-dup.**

**Depends-on**: #2. **Estimate**: 2 days.

---

## 5. Offline outbox + "pending" state with retry

**Description**: app-level outbox over the message doc + `status` (single source of
truth). Renders "pending" (clock icon) on no signal; bounded auto-retry/backoff;
auto-delivers on reconnect. The deliberate seam for the future mesh spec.

**Done-when**: integration test toggles connectivity — a message sent offline shows
pending and delivers **within 10s** of reconnect, with no duplicate or loss. **Maps
to spec gate: offline-queue drain < 10s.**

**Depends-on**: #4. **Estimate**: 1.5 days.

---

## 6. Cloud Function fan-out + FCM push

**Description**: `onMessageCreated` updates conversation summary (last message,
unread counts; batched read-receipt strategy) and sends **FCM** to recipient devices.
FCM is an accelerator — receipt still works via listener if push fails. All logs
**PII-redacted**.

**Done-when**: message create triggers summary update + push in the emulator; a
push-disabled test still delivers via listener on foreground. **Maps to plan
graceful-degradation (FCM not source of truth).**

**Depends-on**: #4. **Estimate**: 1.5 days.

---

## 7. PII-redacted structured logging

**Description**: structured logging across client + Functions with redaction by
default — never the message body, phone numbers, or other PII. Emit redacted metrics
events (`message.sent/delivered`, verification funnel, `outbox.drained`).

**Done-when**: `test/privacy/log_redaction_test` scans emitted logs across send,
receive, fan-out, and auth paths and asserts **zero** bodies/phone numbers/PII.
**Maps to spec gate: zero PII in logs (blocks merge). Privacy-posture sign-off
(Herman).**

**Depends-on**: #3, #4, #6. **Estimate**: 1 day.

---

## 8. Reliability soak test (zero loss / dup / reorder)

**Description**: automated 1,000-message soak across multiple emulator clients and a
full 8-member group; asserts zero loss, zero duplicates (post de-dup), zero
out-of-order; load-checks fan-out cost at the group ceiling.

**Done-when**: `test/reliability/soak_test` passes and is wired as a **merge-blocking**
CI gate. **Maps to spec gates: zero loss / dup / reorder.**

**Depends-on**: #5, #6. **Estimate**: 2 days.

---

## 9. Verification false-reject eval

**Description**: genuine-signup eval set exercising the OTP + mutual-invite gate
(incl. edge cases: ret--retry, slow OTP, not-yet-mutual). Measures false-reject rate;
provides a retry/appeal path for blocked genuine users.

**Done-when**: `test/auth/false_reject_eval` runs and asserts false-reject **< 1%** on
the seed set; runs on PRs touching auth. **Maps to spec gate: <1% false-reject.**

**Depends-on**: #3. **Estimate**: 1 day.

---

## 10. Latency + degradation monitoring (canary-ready)

**Description**: instrument send-to-delivered latency (p95), delivery-fail rate,
verification false-reject rate, outbox drain time. Dashboards + drift alerts (the
silent-degradation guard).

**Done-when**: a canary run surfaces p95 send-to-delivered and the degradation
metrics on a dashboard; alert fires on a synthetic latency regression. **Maps to spec
gate: p95 < 2s (canary) + silent-degradation detection.**

**Depends-on**: #6, #8. **Estimate**: 1 day.

---

## 11. Feature flag + rollback wiring

**Description**: `messaging_core_enabled` via Remote Config, off by default, per-account
override. Automatic rollback on any hard-zero gate breach (unverified access, message
loss, PII-in-logs) or sustained p95 > 2s. Confirm exact windows with Herman.

**Done-when**: toggling the flag enables/disables the path per account; a synthetic
hard-zero breach triggers auto-rollback and a team alert. **Maps to plan rollback
strategy.**

**Depends-on**: #10. **Estimate**: 1.5 days.

---

## 12. Closed beta → canary rollout

**Description**: deploy behind the flag to friends-and-family (invite-only), then a
small invite-only canary for 24h watching rollback triggers; widen in steps with
quality gates between. Run against the emulator first, then real Firebase.

**Done-when**: canary serves for 24h with all gates green and no rollback. **Maps to
spec launch slice.**

**Depends-on**: #11. **Estimate**: 2 days (mostly monitoring).

---

## Parallelisable work

- **After #1**: #2 is the spine. Nothing else should start before rules exist.
- **After #2**: #3 (auth) and #4 (send/receive) can run in parallel.
- **After #4**: #5 (outbox) and #6 (fan-out/FCM) can run in parallel.
- **#9 (false-reject eval)** can start as soon as #3 lands, in parallel with #5/#6.
- **#7 (log redaction)** trails the paths it audits (#3, #4, #6).

---

## Carried-forward decisions to confirm (don't block start)

- **Delete-for-everyone window** (~1 hour proposed) — fold into #4's status model once
  confirmed.
- **Presence / last-seen** — currently leaning *minimal/none* for MVP; if added, it's a
  new task after #6 (write-cost + privacy impact).

---

## Explicitly not in this list

- **Media** (image / voice / file) — out of scope, future story (per spec).
- **External API + MCP** — separate spec/plan/tasks (`external-api-mcp`).
- **Bluetooth mesh** — separate spec/plan/tasks (`bluetooth-mesh`); only the #5 outbox
  seam is prepared.
- **Opt-in AI smart replies** — separate AI spec/plan/tasks.
- **UI visual design** — product-owned; tasks cover states/data contract, not pixels.
