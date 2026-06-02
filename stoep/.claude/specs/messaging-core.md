# Spec: Messaging core (Stoep)

*The four-extras pattern. Every section is required; don't skip any.*

> **Scope note.** This is the first of three planned specs derived from the original
> brief ("a simple WhatsApp for real people, no bots, with a simple API + MCP
> interface, and Bluetooth mesh when signal is bad"). The brief was split by
> decision into:
> 1. **messaging-core** (this spec) — the human-to-human chat MVP on Firebase.
> 2. **external-api-mcp** (future spec) — third-party API + MCP surface.
> 3. **bluetooth-mesh** (future spec) — offline peer-to-peer relay.
>
> **Constitution flag.** The original brief introduces an external API/MCP surface
> and Bluetooth mesh, neither of which appears in the project Constitution
> (Firebase-only, Firestore as the message store, no logic bypassing security
> rules). Those two specs will require a Constitution amendment and human sign-off
> before planning. This messaging-core spec stays fully within the existing
> Constitution.

---

## Traditional user story

> As a person who wants to chat with my real friends (and not bots or strangers),
> I want a simple, reliable one-to-one and small-group messaging app where every
> account is a verified human,
> So that I can have private, trustworthy conversations without spam, bot accounts,
> or the bloat of a mainstream messenger.

---

## 1. Performance thresholds

Measurable criteria for success. At least one number per category.

- **Delivery latency**: When both sender and recipient are online on good signal,
  end-to-end send-to-delivered latency is **< 2 seconds at p95** (< 5s at p99).
- **Delivery reliability**: **At-least-once delivery with strict per-conversation
  ordering.** No silent message loss. Duplicates are permitted at the transport
  layer but the client **de-duplicates by message ID** so the user never sees a
  double. Zero out-of-order messages within a single conversation as observed by
  the recipient.
- **Verification success (false-reject floor)**: Of genuine human signups that
  complete the flow, **< 1%** are wrongly blocked by the verification gate
  (SMS OTP + mutual contact). This is a quality threshold, not a hard zero.
- **Quality floor (hard rules)**:
  - **Zero** messages delivered to an account that has not passed human
    verification (no unverified account can send or receive). Hard rule.
  - **Zero** plaintext message bodies, phone numbers, or PII in application logs
    (per Constitution). Hard rule.

---

## 2. Graceful degradation

What happens when the ideal outcome can't be delivered.

- **No signal / offline (sender)**: An outgoing message is **persisted locally,
  shown with a clear "pending" state (clock icon), and auto-retried** with backoff
  until connectivity returns, then delivered. The composer is never blocked and a
  message is never silently dropped. *(This is the deliberate hook for the future
  bluetooth-mesh spec: "pending, no infrastructure path" is exactly the state mesh
  will later try to satisfy peer-to-peer.)*
- **Partial connectivity (recipient offline)**: Message is accepted and stored
  server-side; recipient receives it on next connect plus an FCM push. Sender sees
  "sent" (single tick), upgraded to "delivered" (double tick) when the recipient's
  device acknowledges.
- **Push unavailable**: If FCM delivery fails, the message still syncs via the
  Firestore listener on next foreground — push is an accelerator, not the source
  of truth.
- **Verification service degraded**: If SMS OTP delivery is failing, surface a
  clear retryable error and an alternate-channel/"try later" path. Never silently
  create an unverified account to "let the user in."
- **Backend availability**: If Firestore writes fail, the message stays in the
  local pending queue (same path as offline) rather than erroring out the UI.

---

## 3. Learning expectations

> **Honest note:** messaging-core is intentionally **deterministic** — it has no
> ML model and therefore no "personalisation" or "accuracy that improves with
> feedback." The adaptive/AI surface (opt-in smart replies) is a **separate AI
> feature with its own spec** and is explicitly out of scope here. What this
> section covers is the operational signals the core must emit so later features
> and reliability work can learn from real usage.

- **Feedback / telemetry signals**: Capture (PII-redacted) delivery latency,
  delivery-success vs retry-vs-fail counts, offline-queue depth and drain time,
  and verification funnel outcomes (start / OTP-sent / OTP-passed / contact-matched
  / blocked). These are the inputs to the acceptance monitors below.
- **Adaptation timeline**: None for the core itself. Thresholds in section 1 are
  fixed targets, tightened only by an explicit human decision, not by the system
  self-adjusting.
- **Personalisation scope**: None. No per-user model state. (Smart replies, when
  specified, will define their own per-user scope.)
- **Eval set growth**: The verification false-reject and delivery-loss eval cases
  grow from **real production misses** (per Constitution's "evals grow from real
  misses"), not a frozen set.

---

## 4. Failure modes

- **False positive (verification blocks a real human)**: A genuine person is
  rejected at signup (e.g. shared/VoIP number, no mutual contact yet).
  *Mitigation*: keep false-reject < 1% (section 1); provide a clear retry and a
  manual-review/appeal path; never make the rejection silent.
- **False negative (a bot/non-human gets in)**: An automated or fake account slips
  past OTP + mutual-contact. *Mitigation*: require BOTH SMS OTP and a mutual
  invite/contact to transact; rate-limit account creation per number/device;
  monitor for behavioural bot signals (burst messaging, mass-invite) and flag for
  review. No programmatic message sending exists in the core, which removes the
  most common bot vector by design.
- **Message integrity (loss / duplication / reordering)**: A message is lost,
  shown twice, or out of order. *Mitigation*: client-generated stable message IDs +
  server timestamps for ordering; at-least-once delivery with client-side de-dup;
  the local pending queue guarantees a send is never abandoned.
- **Adversarial inputs / abuse**: Spam-invite floods, harassment, or attempts to
  enumerate users by phone number. *Mitigation*: per-account invite and send rate
  caps; block/report flow; never expose whether an arbitrary phone number is a
  Stoep user without a mutual signal (contact-discovery privacy).
- **Privacy leak**: Message bodies or phone numbers landing in logs/crash reports.
  *Mitigation*: structured logging with content redaction by default; assert
  "no raw body in logs" as a tested, hard rule.

---

## Acceptance criteria (mapped to CE)

These become continuous-evaluation gates. Every line corresponds to a monitor.

- [ ] Send-to-delivered latency **p95 < 2s** (both online) — perf eval, runs on canary.
- [ ] **Zero** message loss across a 1,000-message reliability soak test (catastrophic-failure gate, blocks merge).
- [ ] **Zero** observed out-of-order or duplicate messages (after client de-dup) in the same soak test (blocks merge).
- [ ] **Zero** send/receive possible from an unverified account across the auth eval set (catastrophic-failure gate, blocks merge).
- [ ] Verification false-reject rate **< 1%** on the genuine-signup eval set (quality eval, runs on PRs touching auth).
- [ ] **Zero** raw message bodies / phone numbers / PII in logs across the log-redaction eval (catastrophic-failure gate, blocks merge).
- [ ] Offline→online: a queued "pending" message **always** delivers within 10s of connectivity returning, across the offline-queue eval (perf/reliability eval, canary).

---

## Out of scope

- **External API + MCP interface** — separate spec (`external-api-mcp`), requires Constitution amendment.
- **Bluetooth mesh / offline P2P relay** — separate spec (`bluetooth-mesh`), requires Constitution amendment. The "pending" state here is the only mesh-related concession.
- **Opt-in AI smart replies / suggestions** — separate AI feature spec; the Constitution's AI principles govern it.
- **Media beyond text in the MVP cut** — image/voice/file messaging is a fast-follow, not part of the core latency/reliability acceptance bar (revisit once text core is green).
- **Large groups / broadcast** — core targets 1:1 and small friend groups only.

---

## Clarifications

*Added in Phase 3. The spec above is unchanged; this section records resolved
ambiguities, proposed defaults, N/A items, and what remains open. Walked against
`clarify-checklist.md`.*

### Resolved by explicit decision

- **Encryption posture** → **Server-readable (Firestore at-rest).** Messages are
  stored in Firestore, encrypted at rest by Google, readable by backend / Cloud
  Functions. This stays within the current Constitution (Firestore as message
  store, server-side fan-out) and keeps the door open for the future API/MCP to
  read content under proper auth/consent. *Consequence:* Stoep is **not** private
  from the operator; this is a deliberate trade for simplicity and feature
  enablement, not an oversight. (Item 7, 16.)
- **Contact discovery** → **Invite link / QR only.** No address-book upload, no
  phone-number lookup. You connect by sharing a link/QR. This is the most
  privacy-preserving option, stores no contact-graph PII, avoids user enumeration,
  and gives a clean definition of "mutual contact" (both sides accepted an
  invite). (Item 5, 7, 17.)
- **Group size** → **Up to 8 participants.** Keeps fan-out cheap and protects the
  p95 < 2s latency bar; matches the "real, intimate friend groups" framing.
  (Item 1, 16.)
- **Retention / deletion** → **Keep until deleted, with delete-for-everyone within
  a window.** Messages persist server-side until a user deletes; sender can
  delete-for-everyone for a bounded period (exact window TBD at plan time, propose
  ~1 hour). Supports multi-device sync. (Item 8.)

### Resolved by proposed default (flag if you disagree)

- **Who, exactly (segments)?** One experience for all verified users. No free/paid
  or role tiers in the core. (Item 1.)
- **First-time / cold-start experience.** New user completes SMS OTP, then lands on
  an empty chat list with a single "invite a friend" action (the invite-link
  flow). No data-dependent behaviour to cold-start since there's no model.
  (Item 2.)
- **What the 20% / failure cases feel like.** The two visible imperfect paths are
  (a) a "pending" message on bad signal — clearly marked, never silently lost; and
  (b) a verification block — clearly explained with retry/appeal. Both are
  *obviously-not-sure*, never *silently-wrong*. (Item 3.)
- **"Powered by AI" in UI?** Not in the core — there is no AI here, so no AI
  labelling. (Smart-reply spec will own that.) (Item 4.)
- **Where message/identity data lives.** Firestore: a `users` collection (verified
  identity, no contact graph) and per-conversation message subcollections;
  client-generated stable message IDs; server timestamps drive ordering. (Item 6.)
  *Note: data-model/schema is human-owned per Constitution — this is a starting
  proposal for the plan, not a final schema.*
- **Data freshness.** Real-time via Firestore listeners; no aggregation across
  users. (Item 8.)
- **Blast radius of a wrong outcome.** Worst cases: a real human wrongly blocked
  (friction, recoverable via appeal) or a message delayed (pending, recoverable).
  No safety-critical surface. Mitigation effort is matched accordingly. (Item 16.)
- **Silent degradation detection.** Section-1 thresholds are monitored continuously
  (latency p95, delivery-fail rate, verification false-reject rate, offline-queue
  drain time); a sustained regression on any triggers an alert. (Item 19.)
- **Launch slice.** Internal/friends-and-family closed beta first, then a small
  invite-only canary, before any wider opening. (Item 20.)
- **Rollback trigger.** Auto-rollback on a sustained breach of any hard-zero gate
  (unverified access, message loss, PII-in-logs) or latency p95 > 2s for a defined
  window. Exact windows set at plan time. (Item 21.)

### N/A — deterministic core, no model

- **Which model / why (9), deterministic vs probabilistic (10), prompt stability
  (11), tool use (12), confidence meaning (13), threshold rationale for confidence
  (14), who sees confidence (15), model-provider downtime (18), A/B test /
  null-hypothesis (22), who owns model upgrades (24).** None apply — messaging-core
  has no LLM/model. These items move to the **smart-reply AI spec**. (One nuance:
  item 18's spirit — third-party-dependency downtime — *is* covered for the SMS-OTP
  and FCM providers in Section 2's graceful-degradation.)

### Resolved ownership / scope

- **Sign-off owner (item 23, 25):** **Herman** owns sign-off for the Firestore
  security rules, the verification/auth flow, and the privacy posture
  (server-readable + invite-only). Per Constitution these remain human-owned.
- **Media (image / voice / file):** **Confirmed out of scope** for messaging-core —
  it is a future story, not part of the core acceptance bar.

### Still open

- **Delete-for-everyone window** (proposed ~1 hour) — confirm at plan time.

- **Web client** — mobile (iOS/Android) first; web is optional per Constitution.
