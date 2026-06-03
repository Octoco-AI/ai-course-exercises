# Spec: External API + MCP (Stoep)

*The four-extras pattern. Every section is required; don't skip any.*

> **Scope note.** This is the second of three specs from the original brief. It
> covers the outward-facing **RESTful API and MCP interface** that lets verified
> third-party ("value-add") systems integrate. The chat MVP is `messaging-core`;
> offline relay is `bluetooth-mesh`.
>
> **Constitution status (AMENDED — ratified).** The Constitution has been amended to
> add the **Integration surface** pillar and **Integration partner principles**. This
> spec now reflects that amendment. The binding rules:
> - **Approved partners MAY send transactional messages directly to users** (no
>   per-message human tap) — but **transactional only** (confirmations, OTPs,
>   reminders, alerts). Never marketing/bulk/unsolicited. Verified **AND**
>   human-approved (allow-list, revocable) — no self-serve sending.
> - **Assistive integrations acting on a user's behalf remain draft-only** — they
>   propose, the human sends. A partner still cannot send *as the user* to others.
> - Partner messages must be **visibly segregated** from human friend messages; users
>   can **mute/block** any partner; opt-out is honoured immediately.
> - *"No business logic that bypasses Firestore security rules."* → API access is
>   gated by the **same** per-conversation membership rules as the client.

---

## Traditional user story

> As a developer of a value-add system (e.g. a CRM, a booking system, a
> personal-assistant tool),
> I want a simple, secure RESTful API and an MCP interface that, with a Stoep user's
> explicit consent, lets me read their conversations, propose draft messages, and —
> if my integration is approved — deliver transactional service messages directly to
> the user,
> So that I can build useful integrations on top of Stoep without ever sending
> marketing/spam, impersonating a human friend, sending *as* the user to others, or
> touching data the user hasn't consented to share.

### Two distinct write paths (keep them separate)

1. **Assistive draft** (any consented integration): create a draft in a human-to-human
   conversation; the **human approves and sends**. Never auto-sends.
2. **Transactional send** (approved partners only): the partner delivers its *own*
   service message **to** a consenting user (e.g. "Your booking is confirmed"). No
   per-message human tap, but transactional-only, clearly labelled as a service
   message, and mutable/blockable by the user.

---

## 1. Performance thresholds

- **Read latency**: authenticated REST read (e.g. recent messages for a consented
  conversation) **p95 < 1s** (p99 < 2s).
- **Availability**: **99.9%** monthly for the API + MCP surface (~43 min/month error
  budget), measured at the edge.
- **Rate limit**: default **60 req/min per integration per consenting user**, burst
  120; over-limit returns **HTTP 429 + `Retry-After`**. Higher tiers by approval.
- **Webhook delivery**: **at-least-once**, exponential-backoff retries over ~24h,
  partner de-dupes by event ID; polling cursor as the reconciliation fallback.
- **Quality floors (hard rules)**:
  - **Zero** cross-user data access — an integration can reach **only the consenting
    user's own data**, scoped by granted OAuth scopes. Hard rule.
  - **Zero** sends *as the user to others* — assistive integrations are draft-only;
    only a human sends a user's conversational message. Hard rule.
  - **Zero** direct sends from a non-approved integration; only **allow-listed,
    approved partners** may transactional-send, and **only** message types
    classified transactional (never marketing/bulk/unsolicited). Hard rule.
  - **Zero** partner messages that are not visibly labelled as service messages
    (no impersonating a human friend). Hard rule.
  - **Zero** access without a valid app credential **and** an unexpired user consent
    grant. Hard rule.
  - **Zero** raw message bodies / phone numbers / PII in API/gateway logs (per
    Constitution). Hard rule.

---

## 2. Graceful degradation

- **Rate-limit hit**: return `429` + `Retry-After`; never silently drop or block
  indefinitely. Document backoff guidance.
- **Webhook endpoint down/slow**: retry with backoff for ~24h; on exhaustion, stop
  pushing and rely on the **polling cursor** so the partner can reconcile — no event
  silently lost.
- **Auth degraded** (token endpoint or consent service struggling): reject with a
  clear `401/503` and retry guidance; **never** fall back to an unauthenticated or
  broader-scope path.
- **Partial backend availability**: if a downstream read fails, return a typed error
  for that resource rather than a 500 for the whole batch; support cursor-resume.
- **MCP transport unavailable**: MCP is a thin facade over the same REST/permission
  core; if MCP is down, REST still serves (and vice-versa). MCP never has powers REST
  doesn't.

---

## 3. Learning expectations

> **Honest note (updated in Phase 3):** the API surface itself is **deterministic**,
> with **one exception**: the partner-message **misuse/abuse classifier** (see
> Clarifications) is an AI/ML monitoring surface. It is *advisory + monitoring*, never
> the primary gate (the primary gate is partner-declared message type + audit), so a
> classifier error cannot itself let spam through silently — but it needs its own
> small acceptance suite per the Constitution's evaluation norms.
> Drafts that an integration creates may themselves be AI-generated *on the
> partner's side*, but that's the partner's system; Stoep's API just stores a clearly
> labelled draft for the human. The Constitution's AI principles (App Check, opt-in,
> labelling) govern Stoep's *own* smart-reply feature, a separate spec.

- **Feedback / telemetry signals**: per-integration request volume, error rates,
  rate-limit hits, latency, webhook delivery success/retry/drop, consent
  grant/revoke events, draft-created vs draft-approved-by-human ratio (the signal
  that an integration is actually useful and not spammy), partner transactional-send
  volume + message-type classification outcomes, and per-partner mute/block/opt-out
  rates (the spam-creep early warning). All **PII-redacted**.
- **Adaptation timeline**: none — thresholds are fixed, changed only by explicit
  human decision.
- **Personalisation scope**: none server-side.
- **Eval set growth**: abuse/scope-bypass eval cases grow from real production
  incidents and audit findings, not a frozen set.

---

## 4. Failure modes

- **Authorization bypass / confused-deputy**: an integration reaches another user's
  or another participant's data. *Mitigation*: enforce per-conversation membership
  rules server-side on **every** call (same rules as the client); scope every token;
  deny-by-default; automated cross-user access eval (hard-zero gate).
- **Consent / token abuse**: stolen or over-broad tokens, no revocation. *Mitigation*:
  short-lived access tokens + refresh; per-user revocable grants; least-privilege
  scopes; full audit log of grant/use/revoke; rotate app secrets.
- **The "bot" vector** (the no-bots rule for human conversation): an integration tries
  to automate or impersonate human-to-human conversation. *Mitigation*: assistive
  integrations are **draft-only** (human sends); a partner can never send **as the
  user** to others; partner transactional sends are a **separate, labelled service
  channel**, not the friend conversation; drafts/partner messages are visibly marked.
- **Transactional-send abuse** (marketing/spam creep, the new attack surface): an
  approved partner drifts from transactional into marketing, bulk, or unsolicited
  messaging. *Mitigation*: approval is allow-listed and **revocable**; per-partner
  send rate caps; message-type classification + content-drift monitoring; mandatory
  per-user **mute/block** and opt-out honoured immediately; repeated violations trip
  throttling and human review (Herman). Non-approved integrations cannot send at all.
- **Scraping / enumeration**: a partner harvests data or probes for users.
  *Mitigation*: rate limits; no endpoint reveals whether an arbitrary phone/number is
  a Stoep user; consent-scoped reads only; anomaly monitoring on volume/spread.
- **Webhook security**: spoofed or replayed event deliveries; SSRF via partner URLs.
  *Mitigation*: HMAC-signed payloads + timestamp/nonce anti-replay; partner verifies
  signature; outbound allow-listing / SSRF protections on webhook registration.
- **Privacy leak in logs**: bodies/PII in gateway or partner-facing logs.
  *Mitigation*: redaction by default; tested hard-zero gate.

---

## Acceptance criteria (mapped to CE)

- [ ] Authenticated read **p95 < 1s** (perf eval, canary).
- [ ] **Zero** cross-user / cross-scope data access across the authorization eval set (catastrophic-failure gate, blocks merge).
- [ ] **Zero** ability to send *as the user to others* — assistive path is draft-only across the write-capability eval set (catastrophic-failure gate, blocks merge).
- [ ] **Zero** direct sends from a non-approved integration; only allow-listed partners can transactional-send (authz eval, blocks merge).
- [ ] **Zero** non-transactional (marketing/bulk) partner sends across the message-classification eval set; violations are rejected/flagged (catastrophic-failure gate, blocks merge).
- [ ] **Zero** partner messages rendered without a service label / mutable+blockable controls (UX-contract eval, blocks merge).
- [ ] **Zero** access without valid app credential + unexpired user consent (auth eval, blocks merge).
- [ ] Rate limiting returns `429` + `Retry-After` exactly at the configured ceiling (perf/abuse eval, on PR).
- [ ] Webhook **at-least-once** proven: a transiently-down endpoint receives every event after recovery, de-duped by ID (reliability eval, canary).
- [ ] Webhook signatures verify and replayed/forged deliveries are rejected (security eval, blocks merge).
- [ ] **Zero** raw bodies / phone numbers / PII in API + gateway logs (catastrophic-failure gate, blocks merge).
- [ ] **99.9%** availability sustained over the canary window (SLA monitor, prod).

---

## Out of scope

- **Sending *as the user* to others / automating human conversation** — forbidden by
  the Constitution; the assistive path is draft-only. (Approved-partner *transactional
  service* send IS in scope — see the user story.)
- **Marketing / promotional / bulk / unsolicited partner messaging** — forbidden by
  the Constitution; not a future relaxation.
- **Bluetooth mesh** and **messaging-core internals** — separate specs.
- **Stoep's own AI smart replies** — separate AI spec; this API only stores
  partner-supplied drafts.
- **A public developer self-serve marketplace / billing** — first cut is
  verified-partner onboarding (manual/approved); self-serve and monetisation are a
  later iteration.
- **GraphQL / gRPC surfaces** — REST + MCP only for now.
- **Media payloads over the API** — text + metadata first (mirrors messaging-core's
  media-deferred decision).

---

## Clarifications

*Added in Phase 3. The spec above is unchanged except the Learning honest-note (which
gained the classifier exception). Walked against `clarify-checklist.md`.*

### Resolved by explicit decision

- **Message classification (transactional vs marketing)** → **Hybrid: partner-declared
  type + automated misuse classifier, lenient-but-fast-to-act.** Primary gate is the
  partner tagging each message's type, recorded in an audit trail; a secondary
  **automated content classifier** monitors for drift/misuse and flags/throttles fast.
  Deliberately more permissive up front (don't block legitimate sends) but quick to
  detect and act on abuse. *Consequence:* the classifier is an **AI surface** — it
  needs its own small acceptance suite (precision on marketing-detection) and is
  advisory, never the silent primary gate. (Items 9–14, 16, 17.)
- **First contact / no prior relationship** → **Requires prior opt-in / linking.** A
  user must explicitly link a partner (e.g. "connect my booking account") before any
  partner message can be delivered. **No cold outreach.** This makes "consent" concrete
  and is the strongest structural anti-spam control. (Items 1, 2, 16, 17.)
- **Approval / revocation of send privileges** → **Herman + a small group of delegated
  reviewers, with an audit trail.** Allow-listing and revocation are human-owned;
  delegation scales review without losing accountability. (Items 23, 25.)

### Resolved by proposed default (flag if you disagree)

- **Who, exactly (segments)?** Three actor classes: (a) read-only/analytics
  integrations, (b) assistive draft integrations, (c) approved transactional-send
  partners. Capability is gated by OAuth scopes + allow-list tier. (Item 1.)
- **First-time integration experience (cold-start).** Partner registers app → gets
  client credentials → requests scopes → each user grants consent via OAuth2; sending
  requires the additional approval tier. Empty-state is read/draft until approved.
  (Item 2.)
- **What drives each decision (inputs).** Authorization = app credential + user consent
  grant + conversation membership (same rules as client). Send-eligibility = approval
  tier + partner-declared message type + prior-link check. (Item 5.)
- **Where data lives / freshness.** Same Firestore as messaging-core, read through the
  same security rules; real-time via webhooks, reconcilable via polling cursor.
  (Items 6, 8.)
- **PII.** Consent-scoped, own-user-data only; partner messages and logs redacted;
  no endpoint reveals whether an arbitrary number is a Stoep user. (Items 7, 17.)
- **Classifier confidence + who sees it.** Confidence is internal/monitoring only —
  surfaced to the abuse-review queue (Herman + reviewers), never to end users or
  partners as a gate. Threshold starts conservative and is calibrated from real
  incidents (treat first weeks as calibration). (Items 13, 14, 15.)
- **Provider downtime.** If the classifier/model is down, fall back to
  declared-type + audit (the primary gate) and queue for later re-scan — sends are not
  blocked, abuse detection is delayed not skipped. (Item 18.)
- **Silent degradation.** Monitor marketing-leak rate (audited samples), per-partner
  mute/block/opt-out rates, and classifier precision drift; sustained regression
  alerts. (Item 19.)
- **Launch slice.** A single friendly design-partner integration in a closed beta
  before opening to the delegated-review allow-list. (Item 20.)
- **Rollback trigger.** Auto-revoke a partner on a confirmed marketing/spam breach;
  platform-level rollback on any hard-zero gate breach (cross-user access, send-as-user,
  unlabelled partner message, PII-in-logs). (Item 21.)

### N/A — deterministic where it counts

- **Deterministic vs probabilistic (10), prompt stability (11), tool use (12)** apply
  *only* to the misuse classifier, not the core API. The classifier should run at a
  stable, versioned config; a change to it triggers an eval re-run. **A/B test (22)**
  not needed for the API; may apply to classifier-threshold tuning later.

### Still open

- **Classifier build-vs-buy and model choice** — defer to Plan (could be a rules-first
  detector with an LLM/Gemini check on suspicious cases; aligns with the Firebase AI
  Logic stack). Flag: this is the one genuine AI sub-component and may deserve its own
  spec if it grows.
- **Exact transactional message-type taxonomy** (which template categories count as
  transactional) — Herman to define the initial allow-list at Plan time.
- **Delegated-reviewer roster** — who, specifically, beyond Herman.
