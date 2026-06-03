# Plan: External API + MCP (Stoep)

*Technical approach. Derived from `specs/external-api-mcp.md` and its Clarifications;
authored before any code.*

---

## Summary

Expose a thin, partner-facing **REST API** and an **MCP server** that are both
facades over one shared **permission + capability core** running in Cloud Functions
(or Cloud Run behind API Gateway). Every call is gated by app credentials + per-user
**OAuth2** consent and the **same Firestore security rules** as the client. Three
capability tiers — read-only, assistive **draft** (human sends), and approved-partner
**transactional send**. Partner sending requires prior user **linking** (no cold
outreach), partner-declared message types as the primary gate, and a lenient
**misuse classifier** (rules-first + Gemini on suspicious cases) as a fast-acting
monitor. Real-time via signed **webhooks** with a polling-cursor fallback.

---

## Approach

- **Surface**: REST (OpenAPI-described) + an **MCP server** that is a *thin facade* —
  MCP tools map 1:1 onto the same internal capability functions REST uses. MCP never
  has powers REST lacks (per spec).
- **Hosting**: API Gateway / Cloud Endpoints in front of **Cloud Functions** (or
  Cloud Run for the long-lived MCP server), staying within the Firebase/GCP stack.
- **Auth**: **OAuth2 authorization-code + PKCE** for per-user consent; app
  client-ID/secret for app identity; **short-lived access tokens + refresh**; scoped
  grants, per-user revocable. Token introspection in the gateway; capability checks +
  Firestore rules in the core. No raw secrets in any client bundle (Constitution).
- **Capability tiers** (enforced server-side, deny-by-default):
  1. **read** — consent-scoped reads of the user's own data.
  2. **draft** — create a draft in a human conversation; human sends in-app.
  3. **transactional-send** — allow-listed partners only; sends the partner's own
     labelled service message to a *linked* user.
- **Transactional-send pipeline**: `partner → declare message type (template/tag) →
  prior-link check → primary gate (type allow-list + audit log) → classifier monitor
  (async, non-blocking) → write labelled service message → user mute/block honoured`.
- **Misuse classifier** (the one AI sub-component): **rules-first** (keyword/heuristic
  + template conformance) with a **Gemini check (Firebase AI Logic)** on suspicious or
  free-form cases. **Advisory/monitoring, not the blocking gate** — a classifier
  outage falls back to declared-type + audit and queues a re-scan. Versioned config;
  change triggers eval re-run.
- **Why this over alternatives**: facade-over-shared-core avoids two divergent
  permission implementations (REST vs MCP drifting is a classic security bug);
  rules-first-then-LLM keeps the classifier cheap, deterministic on the common path,
  and only spends a model call on the ambiguous tail.

---

## Data flow

```
partner app ──▶ API Gateway (authn: app cred + OAuth token introspection, rate limit)
                     │
                     ▼
            capability core (Cloud Functions / Run)
              │  scope check + Firestore security rules (same as client)
              │
   ┌──────────┼───────────────────────────────┐
   ▼          ▼                                ▼
 READ       DRAFT                       TRANSACTIONAL-SEND
 (Firestore  (write draft doc,           (declare type ▶ prior-link check ▶
  read)       human approves in app)      type allow-list + audit ▶ write
                                          labelled service msg)
                                                 │
                                                 ▼ (async, non-blocking)
                                          misuse classifier (rules ▶ Gemini)
                                                 │ flag/throttle/queue-review
                                                 ▼
   events ──▶ webhook dispatcher (HMAC-signed, at-least-once, backoff ~24h)
                     └── polling cursor (reconciliation fallback)

   (all paths: PII-redacted structured logs + audit trail)
```

---

## Integration points

- **Reads from**: messaging-core Firestore (`conversations`, `messages`, `users`) via
  the same security rules; `oauth_grants`, `partner_apps` (allow-list + tier),
  `partner_links` (user↔partner opt-in).
- **Writes to**: draft messages (in conversations), labelled **service messages**,
  `audit_log` (grant/use/revoke/send), `webhook_deliveries`, classifier verdicts.
- **Events emitted**: `message.created`, `draft.created`, `draft.approved`,
  `partner.message.sent`, `consent.granted|revoked`, `partner.blocked` — all redacted.
- **External**: OAuth2 token endpoint, **Gemini via Firebase AI Logic** (classifier
  tail only), partner webhook endpoints (outbound, SSRF-guarded).
- **Constitution-bound, human sign-off (Herman + reviewers)**: security rules covering
  partner access, partner allow-list/tier, the transactional message-type taxonomy.

---

## Eval strategy

Every spec acceptance line maps to a monitor.

- **Pre-deployment (every PR, emulator + test gateway)**:
  - `authz_eval` — cross-user / cross-scope access attempts → **zero** reach. Blocks merge.
  - `write_capability_eval` — assistive path cannot send as-user-to-others; non-approved
    integration cannot transactional-send. **Zero**. Blocks merge.
  - `message_classification_eval` — labelled marketing/bulk samples must be
    rejected/flagged by the **primary gate** (declared-type + allow-list). **Zero**
    non-transactional sends. Blocks merge.
  - `classifier_acceptance_suite` — the AI sub-component's own set: marketing-detection
    **precision/recall** on a seed corpus; runs on classifier-config change.
  - `ux_contract_eval` — every partner message carries a service label + mute/block
    controls. **Zero** unlabelled. Blocks merge.
  - `webhook_security_eval` — forged/replayed deliveries rejected (HMAC + nonce). Blocks merge.
  - `log_redaction_eval` — **zero** bodies/PII in API + gateway logs. Blocks merge.
- **Canary / production**:
  - Read latency **p95 < 1s**; **99.9%** availability (SLA monitor).
  - Webhook **at-least-once** proven against a transiently-down endpoint.
  - Rate limit returns `429` + `Retry-After` at the ceiling.
  - **Spam-creep monitors**: marketing-leak rate (audited samples), per-partner
    mute/block/opt-out rate, classifier precision drift.
- **Eval growth**: abuse/scope-bypass cases grow from real incidents (Constitution).

---

## Rollout strategy

- **Pre-launch**: all blocking evals green; run against the **Firebase emulator** +
  a test OAuth client; security review of partner rules + webhook handling.
- **Closed beta**: a single friendly **design-partner** integration, read+draft first,
  then transactional-send once the classifier + audit are live.
- **Allow-list opening**: widen to delegated-review-approved partners in steps, each
  starting read/draft, transactional-send granted only after review.
- **Feature flags**: `api_external_enabled`, `partner_transactional_send_enabled`
  (per-partner), off by default.
- **Rollback / auto-revoke**: confirmed marketing/spam breach → **auto-revoke that
  partner's send tier**; platform rollback on any hard-zero gate breach (cross-user,
  send-as-user, unlabelled message, PII-in-logs).
- **Graceful degradation**: `429` over limit; webhook retry→poll; classifier down →
  declared-type+audit + queued re-scan (sends not blocked, detection delayed).

---

## Risks and mitigations

1. **Risk**: REST and MCP permission logic drift, opening a hole in one but not the
   other. **Mitigation**: single shared capability core; MCP/REST are facades only;
   `authz_eval` runs against **both** surfaces.

2. **Risk**: "transactional" is gamed — partners slip marketing through declared-type
   tagging. **Mitigation**: pre-registered template allow-list as the structural gate;
   classifier monitor + audited sampling; auto-revoke on confirmed breach; prior-link
   requirement removes cold-outreach entirely.

3. **Risk**: the misuse classifier (AI) is wrong — false-negatives let spam through,
   false-positives throttle legitimate transactional sends. **Mitigation**: it's
   advisory only (never the silent gate); rules-first keeps the common path
   deterministic; its own acceptance suite + calibration period; human review queue.

4. **Risk**: OAuth/token compromise → broad data exposure. **Mitigation**: short-lived
   tokens + refresh, least-privilege scopes, per-user revocation, full audit log,
   anomaly monitoring; secrets never in client bundles.

5. **Risk**: webhook SSRF / spoofing / replay. **Mitigation**: HMAC-signed payloads +
   timestamp-nonce anti-replay; outbound URL allow-listing/validation; partner-side
   signature verification documented.

6. **Risk**: partner access bypasses Firestore security rules via the API path.
   **Mitigation**: the core enforces the *same* rules as the client — no privileged
   bypass; rules unit-tested; explicit `allow ... : if true` lint check.

---

## Cost estimate

- **REST/MCP**: Firebase infra (Functions invocations, Firestore ops, gateway). Read-
  mostly; cost lever is webhook fan-out + audit-log write volume.
- **Classifier**: rules path is ~free; **Gemini calls only on the suspicious/free-form
  tail** — bounded by transactional-send volume × suspicious-rate. Prompt-cache the
  classifier system prompt to cut token cost. Firm numbers once send volume is modelled.
- No model cost on read/draft paths.

---

## Open questions

Carried from Phase 3 (time-boxed; don't block start):

- **Classifier build-vs-buy + model tier** — lean rules-first + Gemini Flash on the
  tail; confirm at build. May graduate to its own spec if it grows.
- **Transactional message-type taxonomy** — Herman defines the initial template
  allow-list.
- **Delegated-reviewer roster** — who beyond Herman, and their audit obligations.
- **MCP hosting shape** — Cloud Run long-lived server vs Functions; finalise with the
  transport choice.

---

## Out of scope (for the plan)

- Self-serve developer marketplace / billing — verified+approved onboarding first.
- GraphQL / gRPC surfaces — REST + MCP only.
- Media payloads — text + metadata first.
- The classifier's deep ML lifecycle (retraining infra) — start rules+LLM; revisit if
  it becomes a standalone spec.
