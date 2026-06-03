# Stoep — WhatsApp clone for real friends

A simple, straightforward messaging app for communication amongst real friends, built on a Firebase backend.

---

## Constitution

*The rules every feature in this project must follow. Claude Code reads this at the start of every session via CLAUDE.md.*

### Architecture

- **Client**: Flutter (Dart), cross-platform (iOS / Android, web optional). State management via a single agreed approach (e.g. Riverpod or Bloc) — pick one and stay consistent.
- **Backend**: Firebase — **Firestore + Auth** (core message store + identity), **Cloud Functions** (fan-out, push triggers, server-side logic), **FCM** (push notifications), **Storage** (media: images, voice notes, files).
- **AI providers**: **Google Gemini**, via **Firebase's Generative AI service (Firebase AI Logic)**. The Flutter client calls Gemini directly through the Firebase AI Logic SDK, secured by **Firebase App Check**. Chosen for native Firebase integration and minimal backend plumbing.
- **Integration surface**: an outward-facing **RESTful API + MCP interface** for verified, approved third-party ("value-add") systems. Secured by app credentials + per-user OAuth2 consent; subject to the same Firestore security rules as the client. See *Integration partner principles*.
- **Patterns**: Repository pattern between Flutter UI and Firebase; security rules are first-class code, reviewed like any other. No business logic that bypasses Firestore security rules.

### AI feature principles

*Scope is "light AI assist" — optional, opt-in smart replies / message suggestions only. These rules apply to that surface.*

- **Opt-in only**: AI suggestions are off by default. A user explicitly enables smart replies; the friend group's expectation is human conversation, not bot-mediated.
- **Always clearly labelled**: any AI-generated suggestion is visibly marked as a suggestion before a human sends it. The AI never sends a message autonomously.
- **App Check is mandatory**: AI calls are only allowed when App Check is active. If App Check fails, the smart-reply feature degrades gracefully (no suggestions) — it does not fall back to an unprotected path.
- **Confidence / graceful degradation**: if the model is unavailable or low-confidence, the suggestion strip simply doesn't appear — the user types normally. Never a spinner that blocks sending, never a blank composer.
- **Feedback mechanism**: track whether a suggestion was accepted, edited, or ignored (implicit signal) to evaluate quality over time.
- **Human-in-the-loop for everything outward-facing**: AI never sends, deletes, or forwards a message on its own. The human always taps send.

### Integration partner principles

*Scope: the external API/MCP surface used by third-party systems. The "real friends, no bots" rule still governs human-to-human conversation; this section is the **narrow, fenced exception** for service messaging.*

- **Verified AND approved only**: programmatic access requires both a verified app credential and **explicit human approval** (Herman) onto an allow-list. No self-serve sending. Approval is revocable at any time.
- **Approved partners may send directly to users — transactional only**: an approved partner MAY deliver messages to a user without a per-message human tap, but **only transactional messages** (e.g. order/booking confirmations, OTPs, appointment reminders, account alerts). **Never marketing, promotional, bulk, or unsolicited content** — that is grounds for immediate removal.
- **Consent and opt-out**: a partner may only message a user the user has a relationship with / has opted into. Every user can **mute or block** any partner per-conversation; opt-out is honoured immediately. Blocking a partner never affects human-to-human chats.
- **Clearly labelled and segregated**: partner/service messages are **visibly distinguished from human friend messages** (service badge, distinct presentation) so a user is never deceived into thinking a bot is a friend.
- **Read + draft for assistive integrations**: integrations that act *on a user's behalf* in human conversations remain **draft-only** — they propose, the human sends. Direct send is reserved for the partner's *own* transactional service messages TO the user, not for impersonating the user to others.
- **Rate-limited and audited**: partner sends are rate-capped, fully audit-logged (grant/use/revoke), and monitored for abuse (volume spikes, content drift toward marketing). Crossing the line trips throttling and review.

### Never-do items

- Never call Gemini without Firebase App Check enforcement — the App Check gate is what makes client-side calls acceptable. No raw API keys in the client bundle.
- Never log raw message bodies, phone numbers, or other PII — redact content in logs (pragmatic privacy stance).
- Never send an AI-generated message *on a human's behalf in a conversation* without explicit human action — the human always taps send. (This does **not** restrict an approved integration partner's own transactional service messages; see *Integration partner principles*.)
- Never let a partner send marketing, promotional, bulk, or unsolicited messages, and never let a partner message appear as if it came from a human friend.
- Never weaken Firestore security rules to make a feature easier; fix the feature instead.
- Never push directly to `main`; always open a PR.
- Never store secrets / API keys in the client bundle or in the repo.

### Delegation norms

- **Fully delegated**: UI scaffolding, boilerplate, model / serialization classes, repetitive refactors, first-draft docs, test scaffolding.
- **Delegated-with-review**: new feature work, Cloud Functions, Firestore security rules, AI suggestion logic, spec drafts.
- **Owned by a human**: data model / schema decisions, security rules sign-off, privacy choices, anything touching auth or message integrity, and **integration-partner approval / send privileges** (allow-listing and revocation).

### Review expectations

- Read every line — especially Firestore security rules and Cloud Functions (they run with elevated trust).
- Run the app against the Firebase emulator, don't just trust CI green.
- Watch for common AI mistakes: fabricated package imports, wrong Firebase API signatures, silent catch blocks, over-broad security rules (`allow read, write: if true`).

### Evaluation norms

- The AI smart-reply feature ships with a small acceptance suite (suggestion relevance + latency) before it's enabled for anyone.
- Production monitoring for AI: suggestion acceptance rate, latency, fallback (no-suggestion) rate.
- Eval examples grow from real misses; we don't keep a frozen static set.

### Stylistic preferences

- Prefer explicit over clever. Keep widgets small and composable.
- Dartdoc on public APIs; one-line comments only for non-obvious code.
- No emojis in source code or commit messages.
- Imports grouped: Dart SDK, Flutter, third-party packages, first-party — each alphabetised.
