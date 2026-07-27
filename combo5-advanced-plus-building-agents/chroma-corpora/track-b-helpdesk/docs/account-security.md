# Account security

## Password

- Change at: Settings → Account → **Change password**.
- Requirements: at least 10 characters, one number or symbol.
- We don't enforce capitals — research shows they don't improve real-world security.

Stolen or shared with someone you don't trust? Change it immediately. Changing your password **signs out all other devices** (including widgets, which go blank until you re-open the app).

## Two-factor authentication

We support TOTP (time-based one-time password) via any authenticator app: Apple Authenticator, Google Authenticator, 1Password, Authy, and others.

To set up: Settings → Account → **Two-factor authentication** → **Enable**. Scan the QR code with your authenticator. Enter the 6-digit code the app shows to confirm. You'll be given 8 single-use recovery codes — **save these somewhere safe**. If you lose your authenticator, these are your only way back in.

We do **not** support SMS-based 2FA. SIM-swap attacks make it less secure than no 2FA in many cases. TOTP only.

## Suspicious activity

If you see:
- Sign-ins from a device you don't recognise.
- Habits you didn't create.
- Completions on days you didn't open the app.
- Plan changes you didn't make.

**Do this immediately:**

1. Settings → Account → **Sign out everywhere**. This invalidates every session.
2. Change your password.
3. Enable 2FA if you haven't already.
4. Email `security@streakly.app` with details (device names, approximate times). A human will respond within 1 business day.

If you see suspicious activity AND can't sign in (someone may have changed your password), email `security@streakly.app` from the email address on the account. A human will verify identity and restore access.

## Recovering a locked account

"I can't sign in":

- **Forgot password**: tap **Forgot password?** on the sign-in screen. We send a reset link to your email.
- **Lost access to email**: if you used Apple / Google sign-in, reset via those providers. If you used plain email sign-in, contact `support@streakly.app` — we'll work with you but can't always recover the account.
- **Lost 2FA device**: use one of the 8 recovery codes you saved when enabling 2FA. Enter the code at the 2FA prompt.
- **Lost 2FA AND recovery codes**: email `security@streakly.app`. Be prepared to verify your identity with account details (creation date, rough habit count, subscription receipts).

Recovery is rate-limited. After 5 failed attempts we pause recovery for 24 hours to prevent brute-force.

## Sessions and sign-out

- Sessions last 30 days of inactivity. Opening the app resets the clock.
- On Plus, up to 5 active sessions at once (one per device). A 6th sign-in invalidates the oldest.
- On Free, only one active session at a time. Signing in on a new device signs you out of the old one.

## What we'll NEVER do

- **We'll never email you asking for your password.** If you get such an email, it's phishing. Delete it.
- **We'll never DM you on social media.** We don't have social media DMs enabled for support.
- **We'll never call or text you.** All support is email.

Anything claiming to be from Streakly that does the above is not from us. Report phishing to `security@streakly.app`.
