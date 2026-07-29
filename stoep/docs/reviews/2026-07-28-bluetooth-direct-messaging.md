# Design review: Bluetooth direct messaging

**Date**: 2026-07-28
**Reviewer**: staff-engineer design pass (`/review-architecture`)
**Change under review**: local uncommitted work — new untracked file
`stoep/.claude/specs/bluetooth-direct-messaging.md` (453 lines, Phase 2 + Phase 3
complete, no plan or tasks yet)
**Scope**: structure, design, and fit with existing patterns. Style, naming, and
test coverage explicitly out of scope.

---

## Verdict

**needs-rework.**

The skeleton is right and it fits the codebase's grain: BLE is layered onto
`messaging-core`'s existing pending outbox rather than becoming a parallel
messaging system, message identity is reused rather than reinvented, and the
scope cut from "mesh" to single-hop is the correct call. Two decisions need to
change before Phase 4 is worth doing. Both are targeted, not structural.

---

## The single most consequential design decision

> **BLE messages are end-to-end encrypted between devices and sync back to
> Firestore as opaque blobs, creating a second, permanently unreadable class of
> message content.** (Constitution amendment 2; Clarifications, "Key custody and
> recovery".)

### It is not right — as stated

The decision conflates two separable things:

1. **Encrypting and signing the radio hop.** Mandatory and non-negotiable. An
   attacker with a radio nearby can passively sniff BLE. The spec's hard rule
   "zero plaintext message bodies transmitted over the air" is correct and should
   stay exactly as written.
2. **Making the synced-back copy permanently opaque to the server.** A choice,
   and the one that carries all the blast radius. Nothing about (1) requires (2).

The reasons (2) should be reversed:

- **It is not motivated by the stated user need.** The user stories are hike,
  festival, load-shedding, plane, basement, farm. Those are *connectivity*
  problems, not *trust-the-operator* problems. E2E answers a threat model this
  spec never claims (censorship, hostile infrastructure). An irreversible
  architectural commitment should be traceable to a stated need.
- **It contradicts the project's chosen posture.** `messaging-core` decided
  server-readable Firestore *explicitly*, calling it "a deliberate trade for
  simplicity and feature enablement, not an oversight," and partly so
  `external-api-mcp` could read content under consent. This spec does not upgrade
  Stoep's privacy — it makes privacy *arbitrary*: the same conversation with the
  same friend has different recoverability and readability depending on whether
  you happened to have signal.
- **It is irreversible with no migration path.** Once shipped, those blobs are
  unreadable forever. Every future feature — search, backup, web client, partner
  read, abuse review, moderation — inherits a permanent hole in history.
- **The spec's own mitigations are evidence of the smell.** A "distinct delivery
  indicator" (Clarifications) and a scary one-time explainer about unrecoverable
  history are user-visible complexity added to explain an internal bifurcation
  that need not exist. Papering over an inconsistency with UI is a signal the
  inconsistency is the problem.
- **The authenticity argument does not carry it.** BLE means no server-side
  sender check, so binding the message to pinned identity keys matters — but that
  is an argument for **signing**, not for confidentiality-at-rest. You can sign
  with the sender's identity key and still store server-readable.

### The alternative

Establish an ephemeral session key from the already-pinned identity keys, encrypt
**and sign** the BLE hop with it (radio protected, sender authenticated), and on
sync-back upload the message as a **normal, server-readable message doc** under
the same posture as every other Stoep message, keyed by the same stable client-
generated ID.

What that buys:

| | Spec as written | Alternative |
|---|---|---|
| Content classes | Two (one unreadable) | One |
| Constitution amendments needed | Three | Two (amendment 2 disappears) |
| `external-api-mcp` read path | Needs a redacted-placeholder concept | Unchanged |
| CF `onMessageCreated` fan-out / push preview | Cannot summarise a blob | Unchanged |
| Operator-side recovery | Impossible by construction | Preserved |
| Key custody product commitment | Device-only, no recovery, must warn users | None needed |
| Ordering reconciliation | Against opaque blobs | Against readable docs, server-backfillable |

The cost is that BLE messages are operator-readable — which is already true of
every other message in the product. Amendments 1 (transport outside Firebase) and
3 (second discovery vector) remain genuinely necessary and are well argued.

---

## What the spec gets right

- **Reusing the pending outbox as the seam.** `messaging-core` deliberately built
  this hook ("pending, no infrastructure path is exactly the state mesh will later
  try to satisfy peer-to-peer"). This spec plugs into it and frames BLE as an
  *additional delivery path* under the existing queue rather than a second
  delivery state machine. This is the single best structural decision in the
  document and it is why the rating is not worse.
- **Reusing stable client-generated message IDs** for de-dup instead of inventing
  a second identity scheme.
- **Narrowing mesh to single-hop.** Removes multi-hop routing and store-and-forward
  on uninvolved devices — the hardest correctness problem and the worst privacy
  surface — and preserves "no device carries a message it isn't a party to."
- **Gating Phase 4 on human sign-off of the amendments**, placed at the top of the
  document. This is the correct placement of responsibility under *Delegation
  norms* and follows the precedent `external-api-mcp` set with its
  "AMENDED — ratified" header. A human-owned decision is put in front of a human
  rather than quietly assumed.
- **Honest N/A handling for the four-extras template** where no model exists,
  consistent with how `messaging-core` handled the same tension.
- **Splitting acceptance gates into CI-testable logic vs a two-device physical
  matrix**, and refusing to let radio behaviour hide behind CI green. Correct, and
  directly downstream of *Review expectations*.

---

## Under-engineered: cross-transport ordering is a `messaging-core` amendment

Clarifications resolves ordering as "causal ordering per conversation" with
sequence/counter metadata. The reasoning is sound — both alternatives produce
user-visible wrongness — but the change is **undersold as a one-line resolution**.

`messaging-core` states that **server timestamps drive ordering**, and carries a
merge-blocking gate of "zero observed out-of-order messages within a
conversation." Adopting causal ordering does not add to that; it **replaces
`messaging-core`'s ordering key, retroactively, for all messages**. That means
touching the message envelope, the ordering/de-dup soak test, and a live
acceptance gate in a spec that is already planned.

**Action**: promote this to a fourth explicit amendment — an amendment to
`messaging-core`, not just to the Constitution — with its own sign-off line. The
spec already flags it as "the single most subtle piece" and human-owned; the
paperwork should match that framing.

---

## Blast radius not yet accounted for

1. **Cloud Functions fan-out (unmentioned anywhere in the spec).**
   `plans/messaging-core.md` step 3: `onMessageCreated` "updates conversation
   summary (last message, unread counts) and triggers FCM." A conversation-summary
   preview and a push-notification preview **cannot be produced from an opaque
   blob**. This is a concrete breakage with no mitigation in the spec. It
   disappears entirely under the alternative above.
2. **`external-api-mcp` is silently inconsistent today.** The new spec assigns the
   partner API a requirement — "the API must represent unreadable messages
   explicitly (a redacted placeholder) rather than omitting them" — but states it
   in a failure-mode bullet of a *different* spec. `specs/external-api-mcp.md` and
   `plans/external-api-mcp.md` both read `conversations`/`messages` with no notion
   of an unreadable class. If the E2E decision survives review, this must land as
   a real edit to both of those files or it will be lost.
3. **Firestore security rules cannot gate BLE at all.** Acknowledged honestly
   (amendment 1) and the mitigation — equally strict, equally reviewed device-side
   checks — is the right answer. Worth restating plainly: this is a real reduction
   in enforceable trust, and it is inherent to doing BLE at all, so it is a cost
   of the feature rather than a fixable defect.

---

## Open holes worth promoting before Phase 4

- **Re-verification while offline** is correctly labelled "a real hole, not a
  detail," and it is a genuine design contradiction: the identity-key-change
  policy requires re-verification, re-verification requires connectivity, and the
  feature exists for no-connectivity. Without the face-to-face QR path, the
  headline scenario (your friend reinstalled the app, you are both at the
  festival) dead-ends. Promote the QR candidate from "still open" to a decided
  requirement.
- **Attestation lifetime was fixed before revocation was designed.** 7 days is
  chosen, and revocation propagation is left open — so a revoked, banned, or
  compromised account can present valid-looking proof for up to a week. That is
  the wrong order of decisions: the lifetime should be an *output* of the
  revocation design, not an input to it. Reopen the number.

---

## Over-engineering

Little to flag. The document is long (453 lines vs 236 and 259 for its siblings,
with a 150-line Clarifications section), and it front-loads some plan-level detail
into a Phase 2/3 artifact — but every such item (2 KB payload cap, 5-minute
discoverable window, advertisement TTL, local-state schema) is explicitly labelled
a proposal rather than a decision. That is honest, not a defect.

---

## Outcomes

| # | Action | Owner | Gate |
|---|---|---|---|
| 1 | Split the crypto decision: keep encrypt+sign on the radio hop; change sync-back to normal server-readable message docs. Retires amendment 2. | Herman (privacy + data model, human-owned) | Blocks Phase 4 |
| 2 | If amendment 2 is instead upheld, add the Cloud Functions consequence (no summary/push preview from a blob) and edit `specs/external-api-mcp.md` + `plans/external-api-mcp.md` to model an unreadable message class. | Herman | Blocks Phase 4 |
| 3 | Promote causal ordering to an explicit amendment of `messaging-core` (ordering key, message envelope, and the zero-out-of-order gate all change). | Herman (message integrity, human-owned) | Blocks Phase 4 |
| 4 | Decide the offline re-verification path (face-to-face QR, no server). | Herman | Blocks Phase 4 |
| 5 | Reopen attestation lifetime; derive it from the revocation-propagation design instead of preceding it. | Herman | Blocks Phase 4 |
| 6 | Keep as-is: single-hop scope cut, outbox reuse, stable-ID reuse, amendment gating, CI vs physical-matrix split. | — | — |

**Rating: needs-rework** — right shape, two decisions to change, no structural
rewrite required.
