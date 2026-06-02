# Stoep — WhatsApp clone for real friends

A simple, straightforward messaging app for communication amongst real friends, built on a Firebase backend.

---

## Constitution

*The rules every feature in this project must follow. Claude Code reads this at the start of every session via CLAUDE.md.*

### Architecture

- **Client**: Flutter (Dart), cross-platform (iOS / Android, web optional). State management via a single agreed approach (e.g. Riverpod or Bloc) — pick one and stay consistent.
- **Backend**: Firebase — **Firestore + Auth** (core message store + identity), **Cloud Functions** (fan-out, push triggers, server-side logic), **FCM** (push notifications), **Storage** (media: images, voice notes, files).
- **AI providers**: **Google Gemini**, via **Firebase's Generative AI service (Firebase AI Logic)**. The Flutter client calls Gemini directly through the Firebase AI Logic SDK, secured by **Firebase App Check**. Chosen for native Firebase integration and minimal backend plumbing.
- **Patterns**: Repository pattern between Flutter UI and Firebase; security rules are first-class code, reviewed like any other. No business logic that bypasses Firestore security rules.

### AI feature principles

*Scope is "light AI assist" — optional, opt-in smart replies / message suggestions only. These rules apply to that surface.*

- **Opt-in only**: AI suggestions are off by default. A user explicitly enables smart replies; the friend group's expectation is human conversation, not bot-mediated.
- **Always clearly labelled**: any AI-generated suggestion is visibly marked as a suggestion before a human sends it. The AI never sends a message autonomously.
- **App Check is mandatory**: AI calls are only allowed when App Check is active. If App Check fails, the smart-reply feature degrades gracefully (no suggestions) — it does not fall back to an unprotected path.
- **Confidence / graceful degradation**: if the model is unavailable or low-confidence, the suggestion strip simply doesn't appear — the user types normally. Never a spinner that blocks sending, never a blank composer.
- **Feedback mechanism**: track whether a suggestion was accepted, edited, or ignored (implicit signal) to evaluate quality over time.
- **Human-in-the-loop for everything outward-facing**: AI never sends, deletes, or forwards a message on its own. The human always taps send.

### Never-do items

- Never call Gemini without Firebase App Check enforcement — the App Check gate is what makes client-side calls acceptable. No raw API keys in the client bundle.
- Never log raw message bodies, phone numbers, or other PII — redact content in logs (pragmatic privacy stance).
- Never send an AI-generated message without explicit human action.
- Never weaken Firestore security rules to make a feature easier; fix the feature instead.
- Never push directly to `main`; always open a PR.
- Never store secrets / API keys in the client bundle or in the repo.

### Delegation norms

- **Fully delegated**: UI scaffolding, boilerplate, model / serialization classes, repetitive refactors, first-draft docs, test scaffolding.
- **Delegated-with-review**: new feature work, Cloud Functions, Firestore security rules, AI suggestion logic, spec drafts.
- **Owned by a human**: data model / schema decisions, security rules sign-off, privacy choices, anything touching auth or message integrity.

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
