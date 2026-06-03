# Tasks: External API + MCP (Stoep)

*Actionable breakdown of `plans/external-api-mcp.md`. One task = one mergeable change,
~1–2 days. Ordered by dependency; unblocked tasks can start now.*

> **Prerequisite:** depends on `messaging-core` (Firestore data model + security rules)
> existing, and on the Constitution amendment (done). Partner allow-list, partner
> security rules, and the transactional message-type taxonomy are **Herman + delegated
> reviewers** sign-off.

---

## Task conventions

- **Size**: ~1–2 days each. **Done-when**: a passing test or running deployment.
- **Dependencies**: `depends-on: #N`. **Owner**: set at sprint planning.

---

## 1. API gateway + app-credential scaffold

**Description**: stand up the gateway (API Gateway / Cloud Endpoints) in front of a
Cloud Functions/Run capability-core skeleton. App registration (`partner_apps`) with
client ID/secret. Health endpoint. Emulator-runnable.

**Done-when**: a registered app with a valid credential reaches a stub `GET /health`
(200); an unregistered/invalid credential is rejected (401). CI green against the test
gateway.

**Depends-on**: none. **Estimate**: 1.5 days.

---

## 2. OAuth2 per-user consent (auth-code + PKCE)

**Description**: OAuth2 authorization-code + PKCE flow; scoped, short-lived access
tokens + refresh; per-user revocable `oauth_grants`. Token introspection in the gateway.

**Done-when**: a user can grant scoped consent and an integration receives a token;
revocation immediately blocks further calls; expired tokens rejected. Integration tests
cover grant/refresh/revoke. **Maps to gate: zero access without valid credential +
unexpired consent.**

**Depends-on**: #1. **Estimate**: 2 days. *(Auth flow — Herman sign-off.)*

---

## 3. Partner security rules + capability-tier enforcement

**Description**: extend Firestore security rules so partner access obeys the **same**
per-conversation membership rules as the client; deny-by-default. Server-side
capability-tier check (read / draft / transactional-send) keyed off scopes +
`partner_apps` tier. Rules unit tests.

**Done-when**: `authz_eval` proves an integration cannot read cross-user / cross-scope
data and cannot exceed its tier, on the emulator. **Maps to gates: zero cross-user
access; security-rules sign-off (Herman).** Blocks merge.

**Depends-on**: #2. **Estimate**: 2 days.

---

## 4. REST read endpoints (consent-scoped)

**Description**: read endpoints for conversations/messages/contacts the consenting user
owns; cursor pagination; typed per-resource errors (no whole-batch 500).

**Done-when**: a consented integration reads only the user's own data; read **p95 < 1s**
in a load test. Unit + integration tests. **Maps to gate: read p95 < 1s.**

**Depends-on**: #3. **Estimate**: 1.5 days.

---

## 5. Assistive draft write path

**Description**: create a **draft** message in a human conversation; surfaced in the
app for the human to approve/send; never auto-sends; never sends as-user to others.

**Done-when**: `write_capability_eval` proves the path creates drafts only and cannot
deliver as the user. Draft appears in the app marked integration-originated. **Maps to
gate: zero send-as-user-to-others.** Blocks merge.

**Depends-on**: #3. **Estimate**: 1.5 days.

---

## 6. Partner linking (prior opt-in) + allow-list/tier

**Description**: `partner_links` opt-in flow ("connect my <partner> account"); admin
allow-list + tier management for `partner_apps` (read/draft/transactional-send),
revocable, audited. Herman + delegated-reviewer roles.

**Done-when**: a transactional send to a **non-linked** user is rejected; allow-list
add/revoke takes effect immediately and is audit-logged. **Maps to gates: no cold
outreach; zero send from non-approved integration.** Blocks merge.

**Depends-on**: #3. **Estimate**: 2 days. *(Allow-list/tier — Herman sign-off.)*

---

## 7. Transactional message-type taxonomy + template allow-list (primary gate)

**Description**: define the initial transactional template/type taxonomy (Herman);
implement declared-type + template allow-list as the **primary** send gate + audit log
of every send.

**Done-when**: `message_classification_eval` — labelled marketing/bulk samples are
rejected by the primary gate (**zero** non-transactional sends); every send recorded in
`audit_log`. Blocks merge.

**Depends-on**: #6. **Estimate**: 1.5 days. *(Taxonomy — Herman sign-off.)*

---

## 8. Transactional send + service-message labelling + mute/block

**Description**: send pipeline writing a **labelled service message** to a linked user;
visible service badge + per-partner **mute/block/opt-out**, honoured immediately.

**Done-when**: `ux_contract_eval` — every partner message carries a service label +
working mute/block; a muted partner cannot reach the user; blocking a partner doesn't
affect friend chats. **Maps to gate: zero unlabelled partner messages.** Blocks merge.

**Depends-on**: #7. **Estimate**: 2 days.

---

## 9. Misuse classifier (rules-first + Gemini tail) — advisory monitor

**Description**: async, **non-blocking** classifier over partner sends; rules/template
conformance first, **Gemini (Firebase AI Logic)** on the suspicious/free-form tail;
verdicts → review queue + throttle signal. Versioned config. Falls back to
declared-type+audit when the model is down (queues re-scan).

**Done-when**: `classifier_acceptance_suite` runs (marketing-detection precision/recall
on a seed corpus) and is wired to re-run on config change; classifier outage does **not**
block sends. **Maps to: classifier acceptance suite (AI sub-component).**

**Depends-on**: #8. **Estimate**: 2 days. *(AI surface — own eval suite required.)*

---

## 10. Webhooks (signed, at-least-once) + polling cursor

**Description**: webhook registration (SSRF-guarded URLs); HMAC-signed payloads +
timestamp/nonce anti-replay; at-least-once delivery with ~24h backoff; partner de-dupes
by event ID; cursor-based polling fallback.

**Done-when**: `webhook_security_eval` rejects forged/replayed deliveries (blocks
merge); a transiently-down endpoint receives every event after recovery, de-duped
(reliability eval, canary). **Maps to gates: webhook at-least-once + signature
verification.**

**Depends-on**: #4. **Estimate**: 2 days.

---

## 11. MCP server (facade over the capability core)

**Description**: MCP server exposing tools that map 1:1 onto the same capability-core
functions (read/draft/transactional-send), same auth + scope + tier checks. No powers
REST lacks.

**Done-when**: `authz_eval` passes against the **MCP** surface too (parity with REST); an
MCP client performs read + draft within its scope; over-scope attempts denied.

**Depends-on**: #4, #5. **Estimate**: 2 days.

---

## 12. Rate limiting + PII-redacted logging/audit

**Description**: per-integration-per-user rate limits (60/min, burst 120 → `429` +
`Retry-After`); structured logging with redaction; complete audit trail
(grant/use/revoke/send).

**Done-when**: rate limiting returns `429`+`Retry-After` exactly at the ceiling;
`log_redaction_eval` finds **zero** bodies/PII in API + gateway logs (blocks merge).
**Maps to gates: rate limiting; zero PII in logs.**

**Depends-on**: #4. **Estimate**: 1.5 days.

---

## 13. SLA + spam-creep monitoring (canary-ready)

**Description**: dashboards/alerts for read p95, 99.9% availability, webhook
success/retry/drop, and the **spam-creep** signals (marketing-leak rate from audited
samples, per-partner mute/block/opt-out rate, classifier precision drift).

**Done-when**: canary surfaces p95 + availability + spam-creep metrics; alert fires on a
synthetic regression. **Maps to gates: p95<1s, 99.9% availability, silent-degradation
detection.**

**Depends-on**: #9, #10, #12. **Estimate**: 1.5 days.

---

## 14. Feature flags + auto-revoke + closed beta

**Description**: `api_external_enabled`, `partner_transactional_send_enabled`
(per-partner), off by default; auto-revoke a partner's send tier on a confirmed
marketing/spam breach; platform rollback on any hard-zero gate breach. Onboard one
design-partner in closed beta.

**Done-when**: a synthetic confirmed-breach auto-revokes the partner + alerts; design
partner runs read+draft, then transactional-send, with all gates green over the canary
window. **Maps to: rollout + rollback strategy.**

**Depends-on**: #13. **Estimate**: 2 days (mostly monitoring).

---

## Parallelisable work

- **After #1**: #2 is the spine; nothing else before it.
- **After #3**: #4 (reads), #5 (draft), #6 (linking/allow-list) can run in parallel.
- **After #4**: #10 (webhooks), #11 (MCP), #12 (rate limit/logging) can run in parallel.
- **Send chain is sequential**: #6 → #7 → #8 → #9.

---

## Carried-forward decisions to confirm (don't block start)

- **Classifier model tier / build-vs-buy** — lean Gemini Flash on the tail; may graduate
  to its own spec (fold into #9).
- **Transactional message-type taxonomy** — Herman defines initial allow-list (#7).
- **Delegated-reviewer roster** — who beyond Herman (#6).
- **MCP hosting shape** — Cloud Run vs Functions (#11).

---

## Explicitly not in this list

- **Self-serve developer marketplace / billing** — verified+approved onboarding first.
- **GraphQL / gRPC** — REST + MCP only.
- **Media payloads over the API** — text + metadata first.
- **Sending *as the user* to others / automating human conversation** — forbidden by
  the Constitution.
- **Marketing / bulk / unsolicited partner messaging** — forbidden by the Constitution.
- **Classifier deep ML lifecycle (retraining infra)** — start rules+LLM; revisit if it
  becomes a standalone spec.
