# Spec: Bluetooth direct messaging (Stoep)

*The four-extras pattern. Every section is required; don't skip any.*

> **Scope note.** This is the third of the specs derived from the original brief,
> and it fulfils the slot `messaging-core` reserved as `bluetooth-mesh`. It is
> **deliberately narrower than "mesh"**: direct, single-hop, device-to-device only.
> No relaying of a message through an uninvolved third device. The name changed to
> `bluetooth-direct-messaging` to stop "mesh" implying multi-hop scope that is
> explicitly out of scope here.
>
> **Honest note: this is not an AI feature.** There is no model, no inference, no
> personalisation. The four-extras pattern still earns its place because the
> feature *is* non-deterministic — radio discovery is probabilistic, proximity is
> unstable, and delivery is best-effort. The "learning expectations" section is
> therefore operational telemetry, not model adaptation, and says so.

---

## Constitution amendments required

Per *Delegation norms*, data-model, privacy, auth and message-integrity decisions
are **human-owned**. This feature cannot ship under the Constitution as written.
Three amendments need **Herman's explicit sign-off** before Phase 4 planning is
worth doing:

1. **Transport outside Firebase.** The Constitution states *"Backend: Firebase —
   Firestore + Auth (core message store + identity)"* and, in *Never-do items*,
   **"No business logic that bypasses Firestore security rules."** A BLE message
   never touches Firestore, so **no security rule can gate it**. The enforcement
   point moves to the device: peer identity verification, rate caps and block
   lists must be enforced client-side, on a device the user controls. This is a
   genuine weakening of the current trust model, not a technicality. The
   Constitution's intent ("never weaken security rules to make a feature easier")
   is preserved in spirit only by making the device-side checks equally strict and
   equally reviewed.

2. **A class of messages the backend cannot read.** `messaging-core`
   *Clarifications* decided **server-readable Firestore** as the encryption
   posture, partly so `external-api-mcp` could read content under proper consent.
   BLE messages are **end-to-end encrypted between devices** and sync back as
   opaque blobs. Consequence: Stoep will have two content classes, and the partner
   API/MCP surface **cannot** read the BLE class. Any partner or feature that
   assumes it can read all history is wrong from this point on.

3. **A second discovery vector.** `messaging-core` decided **invite link / QR
   only**, explicitly to avoid user enumeration and stranger contact. This feature
   adds a time-boxed, opt-in **"discoverable to nearby people"** mode. That is a
   new (narrow, consent-gated, physically-bounded) enumeration surface and needs
   to be accepted as such.

---

## Traditional user story

> As someone standing near a friend with no usable signal — a hike, a festival, a
> load-shedding blackout, a plane, a basement, a rural farm,
> I want to see which of my Stoep contacts are physically nearby and send them a
> text message directly over Bluetooth,
> So that being offline stops meaning being unable to reach the person standing
> three metres away from me.

Secondary story, from the opt-in discovery decision:

> As someone meeting a new person face-to-face while both of us are offline,
> I want to add them and start a conversation without either of us having signal,
> So that the moment we met isn't lost to "I'll add you when I get bars."

---

## 1. Performance thresholds

Measurable criteria for success. At least one number per category.

All thresholds below assume the agreed MVP envelope: **both devices in
foreground** (app open), **BLE enabled and permission granted**, **line-of-sight
range up to ~10m**.

- **Discovery latency**: A nearby contact appears in the nearby list within
  **10 seconds at p95** (both apps foregrounded, ~10m line-of-sight).
- **Send-to-delivered latency**: Once a peer is discovered, tap-send to
  delivered-acknowledgement is **under 5 seconds at p95**. This is measured from
  an already-discovered peer; discovery time is measured separately above and the
  two are not summed into a single bar.
- **Delivery success rate**: **>=90%** of sends succeed on the first attempt when
  both devices are in range and foregrounded. The remaining <=10% must fail
  *visibly* into the existing pending queue, never silently.
- **Payload**: **Text only.** Proposed cap **2 KB of ciphertext per message**
  (roughly 1,500 plain characters) — *this number is a proposal for Phase 4, not
  a measured limit.* Anything larger, and all media, stays on the online path.
- **Quality floor (hard rules)**:
  - **Zero** messages exchanged with a peer that fails identity verification —
    either a cached pinned identity key (existing contact) or a valid, unexpired
    signed attestation (new contact). Hard rule, inherits `messaging-core`'s
    merge-blocking "no unverified account transacts" gate.
  - **Zero** plaintext message bodies transmitted over the air. Every BLE payload
    is end-to-end encrypted. Hard rule.
  - **Zero** message bodies, phone numbers, BLE hardware addresses, or stable
    device identifiers in logs (per Constitution's PII rule, extended to cover
    radio identifiers). Hard rule.
  - **Zero** discoverability to non-contacts when "discoverable" mode is off.
    Off is the default state. Hard rule.
  - **Zero** background BLE advertising or scanning in the MVP — foreground-only
    is a privacy property here, not just a scope cut. Hard rule for this release.

---

## 2. Graceful degradation

What happens when the ideal outcome can't be delivered. The governing principle,
inherited from `messaging-core`: **the composer is never blocked and a message is
never silently dropped.** Bluetooth is an *additional* delivery path layered onto
the existing pending queue — when it fails, the message simply remains pending,
exactly as it does today.

- **Bluetooth off, or permission denied**: The nearby section is hidden (or shows
  a single explanatory tap-to-enable row). Messaging behaves exactly as it does
  today. The feature never nags on every screen and never blocks sending.
- **No peer in range**: The nearby list is honestly empty with a "searching"
  state and a manual rescan. Sending falls through to the normal pending queue.
  Absence of nearby contacts is a normal state, not an error.
- **Discovery fails while the peer is genuinely nearby** (the >=90% bar's other
  side): manual rescan available; the message queues normally. No dead-end.
- **Transfer interrupted mid-send** (peer walks away, radio drops): the message
  returns to **pending**, and is retried automatically on rediscovery. Because
  message IDs are the same client-generated stable IDs as `messaging-core`, a
  partially-delivered-then-retried message **de-duplicates on the recipient** and
  is never shown twice.
- **Attestation expired, new contact, still offline**: You can see and pair with
  the person, but the contact stays **pending verification** and no messages flow.
  The UI must say plainly why ("we need signal once to confirm this person's
  account"). Existing contacts are unaffected — they rely on identity keys already
  pinned from prior online contact, not on a fresh attestation.
- **App backgrounded**: BLE delivery stops. This is a stated MVP limitation and
  must be surfaced honestly in the feature's explanation, not discovered by users
  as flakiness. Queued messages simply wait.
- **No connectivity for sync-back**: The encrypted blob sits in a local upload
  queue and syncs whenever connectivity returns. Sync-back is never on the
  critical path of delivering the message to the person in front of you.
- **Recipient's other devices**: Until sync-back completes, a BLE-delivered
  message exists only on the two devices that exchanged it. Multi-device history
  is eventually-consistent, and the UI should not pretend otherwise.

---

## 3. Learning expectations

> **Honest note.** As with `messaging-core`, there is **no model and no
> personalisation** here — nothing "learns." What follows is the operational
> telemetry the feature must emit so the thresholds in section 1 can be monitored
> and so the eval set can grow from real field failures, per the Constitution's
> *"eval examples grow from real misses; we don't keep a frozen static set."*

- **Telemetry signals** (all PII-redacted; **no** hardware addresses, no stable
  device identifiers, no bodies): time-to-discover distribution, in-range delivery
  success/failure counts, transfer-abort rate and abort reason, retry-to-success
  counts, attestation rejection counts **by reason** (expired / malformed /
  unknown signer / replay suspected), discoverable-mode activation frequency and
  duration, sync-back queue depth and drain time.
- **Adaptation timeline**: None. Section 1's numbers are fixed targets, tightened
  only by explicit human decision. The system does not self-adjust its own bars.
- **Personalisation scope**: None. No per-user state beyond pinned identity keys
  for known contacts.
- **Eval set growth**: Field failures become eval cases — specifically the
  device/OS-version pairs and physical conditions (through-wall, pocket, crowded
  2.4GHz) where discovery or delivery missed. This matters more than usual here
  because BLE behaviour is *deeply* device- and OS-specific, so the eval matrix is
  expected to grow rather than converge.

---

## 4. Failure modes

- **Ghost peers (false positive discovery)**: A contact shows as nearby after
  they've walked away or powered off, so the user taps send into a void.
  *Mitigation*: advertisement TTL — drop a peer from the nearby list after a small
  number of missed intervals; on send failure, immediately correct the list rather
  than leaving a stale entry.
- **Invisible peers (false negative discovery)**: The contact is genuinely three
  metres away and never appears. This is the feature's signature failure and the
  most damaging to trust. *Mitigation*: the >=90% in-range bar; manual rescan; an
  honest "searching" state instead of a confident empty list; a device/OS eval
  matrix rather than a single reference phone.
- **Impersonation / peer spoofing**: A malicious nearby device claims to be your
  friend and receives a message intended for them. *Mitigation*: pinned identity
  keys for existing contacts (established during prior online contact) and
  server-signed attestations for new ones; reject unknown signers outright. **No
  trust-on-first-use.**
- **Attestation replay**: An attacker captures a valid attestation and replays it
  to pose as a verified account. *Mitigation*: short attestation lifetime plus a
  nonce challenge-response so a captured blob alone is insufficient; monitor
  replay-suspected rejections.
- **Presence tracking / BLE as a beacon**: Stoep's advertising becomes a way to
  track a person's physical movements, or a hardware address lands in a log.
  *Mitigation*: rotating (non-stable) advertised identifiers; foreground-only
  operation in the MVP; discoverable-to-strangers mode is **off by default,
  time-boxed with a visible countdown** (proposed 5 minutes — a Phase 4 number,
  not a decided one); radio identifiers treated as PII in the log-redaction gate.
- **Proximity abuse / stranger spam**: Someone in discoverable mode is flooded by
  a nearby stranger, or harassed in a crowd. *Mitigation*: device-side per-peer
  rate caps; block/report reachable from the nearby list; discoverable mode
  expires on its own without the user remembering to turn it off.
- **Divergent history and cross-transport ordering**: The same conversation now
  arrives via two independent transports with no shared clock, so message order
  between a BLE message and a server message is ambiguous, and the two devices may
  disagree. *Mitigation*: reuse `messaging-core`'s stable client IDs for de-dup;
  ordering needs a defined rule (device timestamp plus causal/sequence metadata).
  **This is not fully solved in this spec** — it is called out for Phase 3/4, and
  it is the item most likely to produce subtle bugs.
- **Unrecoverable history (direct consequence of the E2E choice)**: Sync-back
  blobs are opaque to the server, so losing the device keys means those messages
  are gone permanently — no operator-side recovery is possible. *Mitigation*: be
  explicit with users about it; key management and any recovery mechanism is a
  human-owned decision, deliberately deferred to Phase 4 rather than assumed.
- **Partner API blind spot**: An approved integration reads a conversation and
  silently gets an incomplete history because BLE messages are unreadable.
  *Mitigation*: the API must represent unreadable messages explicitly (a redacted
  placeholder) rather than omitting them, so a partner can never mistake a partial
  history for a complete one.

---

## Acceptance criteria (mapped to CE)

These become continuous-evaluation gates. Every line corresponds to a monitor or
a test.

> **Honest caveat on where these run.** BLE behaviour cannot be validated in CI or
> the Firebase emulator — it needs real radios on real hardware. The gates below
> split into (a) unit/integration-testable logic, which runs in CI, and (b) a
> **two-device physical eval matrix**, which is a manual or device-lab run per
> release candidate. Marking radio behaviour "CI green" would be exactly the kind
> of false comfort the Constitution's *"run the app against the emulator, don't
> just trust CI green"* warns about.

Runs in CI (logic, no radio):

- [ ] **Zero** unencrypted payloads produced by the send path across the crypto
      eval (catastrophic-failure gate, blocks merge).
- [ ] **Zero** peers accepted with a missing, malformed, expired, unknown-signer,
      or replayed attestation across the peer-verification eval set
      (catastrophic-failure gate, blocks merge).
- [ ] **Zero** message bodies, phone numbers, or BLE/device identifiers in logs
      across the log-redaction eval (catastrophic-failure gate, blocks merge).
- [ ] **Zero** duplicate messages shown after an interrupted-then-retried send,
      across the de-dup eval (blocks merge).
- [ ] Device is **not** discoverable to non-contacts whenever discoverable mode is
      off, across the discovery-permission eval (catastrophic-failure gate, blocks
      merge).
- [ ] Discoverable mode **always** self-expires within its window, across the
      timer eval (blocks merge).
- [ ] A failed BLE send **always** leaves the message in the pending queue and
      never blocks the composer, across the degradation eval (blocks merge).

Runs on the two-device physical matrix (per release candidate):

- [ ] Discovery of a nearby contact within **10s p95** at ~10m line-of-sight
      (perf eval).
- [ ] Send-to-delivered within **5s p95** for an already-discovered peer (perf
      eval).
- [ ] **>=90%** first-attempt delivery success in range, foregrounded (reliability
      eval).
- [ ] Interrupted transfer recovers to delivered on rediscovery without user
      intervention (reliability eval).
- [ ] Offline first-contact with a new person succeeds via attestation with **no
      connectivity on either device** (functional eval — this is the secondary
      user story's only proof).
- [ ] Sync-back completes and history reconciles across the sender's other devices
      within a defined window of connectivity returning (reliability eval).

Monitored in production:

- [ ] In-range delivery success rate, discovery-time distribution, attestation
      rejection rate by reason, sync-back drain time — sustained regression on any
      raises an alert.

---

## Out of scope

- **Multi-hop / mesh relay** — no device carries a message it isn't a party to.
  This is the single biggest deliberate cut, and it means "offline" only helps when
  your friend is physically near you.
- **Background discovery, advertising, or receiving** — foreground-only in this
  release, both as scope control and as a privacy property. Revisit only with a
  realistic view of iOS background BLE limits.
- **Media over Bluetooth** — images, voice notes, files stay on the online path.
- **Group conversations over Bluetooth** — BLE send targets a single nearby
  contact (1:1). Group messages stay on the online path even if one member is
  nearby, because partially-delivered group state across two transports is a much
  harder correctness problem. *Flagged as a default, open to challenge.*
- **Wi-Fi Direct / Nearby Connections / AWDL as transports** — this spec is BLE.
  Higher-bandwidth transports are a future option and would reopen the media
  question.
- **Operator-side recovery of BLE message history** — impossible by construction
  given the E2E choice; not a gap to be fixed later.
- **Interoperability with any non-Stoep app or protocol.**
- **Web client** — mobile only; web has no usable BLE story here.

---

## Clarifications

*Added in Phase 3. The spec above is unchanged; this section records resolved
ambiguities, proposed defaults, N/A items, and what remains open. Walked against
`clarify-checklist.md`.*

### Resolved by explicit decision

- **Key custody and recovery** → **Device-only keys, no recovery.** Encryption
  keys never leave the device. Losing the device means those Bluetooth messages
  are permanently unrecoverable, and the blobs already synced to Firestore stay
  unreadable forever. No key escrow, no passphrase, no recovery code — and
  therefore no key-escrow attack surface and no weak-passphrase link in the E2E
  chain. *Consequence:* this must be stated plainly in the UI **before** a user
  relies on BLE messaging, not discovered at the moment of loss. (Items 7, 16.)

- **Cross-transport ordering** → **Causal ordering per conversation.** Each
  message carries sequence/counter metadata so ordering follows what each device
  actually observed. Chosen because the alternatives both produce user-visible
  wrongness: server-timestamp-wins makes offline messages visibly jump position
  after sync, and freeze-in-place lets two participants' devices disagree about
  the same conversation permanently. This **closes the gap flagged in Failure
  modes**. *Flag:* this is the single most subtle piece of the feature. It needs
  careful human review, not delegated implementation — per Constitution,
  message-integrity work is human-owned. (Item 8.)

- **Identity key change (reinstall / new device)** → **Warn and require
  re-verification.** If a contact's pinned identity key changes, Bluetooth
  messaging to that contact **pauses** behind a visible "this contact's device
  changed" notice until re-verified. This is the control that actually prevents
  impersonation: without it, an attacker simply claims to be a reinstalled friend.
  Accepted cost: legitimate reinstalls cause real friction. (Item 17.)

- **Attestation lifetime** → **7 days.** Replay is defended by nonce
  challenge-response, not by a short validity window, so a week costs little
  cryptographically while covering the actual offline scenarios (festival, hike,
  long weekend). *Consequence:* a revoked, banned, or compromised account can
  still present valid-looking proof of verification for up to 7 days when making
  offline first-contact. See *Still open* — revocation propagation needs a design.
  (Items 17, 18.)

### Resolved by proposed default (flag if you disagree)

- **Who, exactly (segments)?** One experience for all verified users. No tiers.
  The feature flag exists for rollout control only, not to differentiate users.
  (Item 1.)
- **Cold start.** A brand-new user with an empty contact graph has nothing to
  discover, so the nearby surface shows only the "meet someone new" affordance.
  The primary user story inherently requires at least one existing contact; the
  secondary (offline first-contact) is what carries a zero-contact user.
  (Item 2.)
- **What the failing 10% feels like.** Always *visibly pending*, never silently
  wrong (spec section 2). Additional rule: never show a peer as "nearby" while
  sends to them are failing — correct the list instead of leaving a confident lie
  on screen. (Item 3.)
- **How users encounter the feature.** No "powered by AI" labelling — there is no
  AI here. But a **one-time explainer is required** before first use, covering
  three things users cannot infer: that it only works with the app open, what
  discoverable mode exposes and for how long, and that this history is not
  recoverable if the device is lost. Permission rationale shown before the OS
  prompt, not after. (Item 4.)
- **What drives the behaviour (inputs).** Exactly four: BLE advertisements from
  nearby peers, locally pinned contact identity keys, the server-issued
  attestation cached at last login, and the user's own discoverable-mode state.
  Nothing else. (Item 5.)
- **Where that data lives.** New **local-only** state: pinned identity keys,
  cached attestation, an **in-memory** nearby-peer list, and an outbound encrypted
  sync queue. Firestore gains only opaque ciphertext blobs plus the existing
  message-envelope metadata. *Per Constitution, data model and schema are
  human-owned — this is a starting proposal for Phase 4, not a decided schema.*
  (Item 6.)
- **PII handling.** Two extensions to the Constitution's PII rule, proposed as
  **hard rules**: (a) BLE hardware addresses and any stable radio identifier are
  treated as PII and never logged; (b) **presence data is never uploaded** — who
  was physically near whom, and when, is not telemetry, not analytics, and not
  stored server-side. The nearby-peer list stays in memory, is never persisted,
  and reaches telemetry only as aggregate counts. This is the most
  attacker-interesting data the feature creates. (Item 7.)
- **Data freshness.** Discovery is real-time with a short advertisement TTL.
  Sync-back is eventually-consistent and explicitly *not* on the critical path of
  delivering to the person in front of you. (Item 8.)
- **What the user sees about delivery state** (items 13–15, translated from
  "confidence"): there are no confidence scores, but BLE-delivered messages have
  **materially different semantics** from normal ones — unreadable to the backend
  and partner API, possibly not yet on the user's other devices, and not
  operator-recoverable. Proposal: they carry a **distinct delivery indicator**,
  not the standard tick. This follows the Constitution's existing labelling
  ethos (AI suggestions visibly marked, partner messages visibly distinguished):
  never let a user assume uniform semantics across visually identical things.
- **Silent degradation.** The realistic mode here is not gradual drift — it is an
  **OS update silently breaking BLE on one platform**. So discovery and delivery
  success must be monitored **segmented by OS version and device model**, with
  alerting on per-segment regression. A global average would hide a total
  single-platform break behind healthy numbers from the other platform.
  (Item 19.)
- **Launch slice.** Internal, then friends-and-family, then invite-only canary —
  and flagged **separately per platform**, because the iOS and Android BLE stacks
  fail in different ways and a problem on one says little about the other.
  (Item 20.)
- **Rollback trigger.** The feature flag must be a true **server-side remote kill
  switch**: a crypto or privacy defect here cannot wait on app-store review and
  user updates. Automatic kill on sustained breach of any hard-zero gate
  (unencrypted payload, unverified peer accepted, PII/presence leak,
  discoverability while off). (Item 21.)
- **A/B test?** No. This is an additive capability, not an optimisation — there is
  no meaningful null hypothesis. Measure adoption, discovery success, and delivery
  success instead. (Item 22.)
- **Who owns "model" upgrades** (item 24, translated to **OS / BLE stack
  upgrades**): on every iOS and Android major beta, the two-device physical matrix
  is re-run before that OS reaches general release. This is the standing
  maintenance cost of shipping a radio feature.

### N/A — no model in this feature

- **Which model and why (9), deterministic vs probabilistic (10), prompt
  stability (11), tool use (12), confidence source (13), threshold rationale for
  confidence (14).** None apply — there is no model, no prompt, and no inference.
  Section 1's thresholds are radio-performance targets, not eval scores.
- **Model provider downtime (18)** — no provider. The *spirit* does apply to the
  one server dependency: **attestation issuance**. If Firebase is unreachable,
  existing contacts keep working entirely offline on pinned keys, and offline
  first-contact keeps working until the cached attestation expires (7 days).

### Resolved ownership

- **Eval suite ownership (item 23):** **Herman** owns the crypto, privacy, and
  peer-verification gates — these are the merge-blocking zeros. The two-device
  physical matrix needs a named per-release owner (see *Still open*).
- **Spec sign-off (item 25):** **Herman** — covering the three Constitution
  amendments, key custody, the ordering rule, and the identity-key-change policy.
  All four are human-owned categories under *Delegation norms*.

### Still open

- **The three Constitution amendments are not yet signed off.** This is the
  explicit gate on Phase 4 — planning against an unamended Constitution would be
  planning something we have not agreed to build.
- **Revocation propagation.** How a revoked or banned account is cut off before
  its 7-day attestation expires. Proposed direction: a revocation list checked on
  every reconnect, with revoked peers dropped from BLE eligibility. Needs design.
- **Re-verification while offline.** The identity-key-change policy and the
  offline-first premise collide: if re-verifying a reinstalled contact requires
  connectivity, then a friend who reinstalled cannot be re-verified in exactly the
  field conditions this feature exists for. A face-to-face path (QR scan between
  the two devices, no server) is the obvious candidate. **Needs a decision at
  plan time** — it is a real hole, not a detail.
- **2 KB ciphertext payload cap** — proposal, not measured.
- **5-minute discoverable-mode window** — proposal, not decided.
- **Advertisement TTL** for dropping stale peers — no number yet.
- **Named owner for the physical device matrix** per release candidate.
- **Group conversations over BLE** — excluded by default in the spec; open to
  challenge if 1:1-only proves too limiting.
