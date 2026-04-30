# Data and privacy

## What we collect

We collect the minimum we need to make Streakly work.

**On every user:**
- Email address and password hash (or Apple/Google identifier for social sign-in).
- Habits you create — title, icon, goal, schedule.
- Daily completions — which days you marked each habit done.
- Basic device info (iOS/Android, app version) so we can debug crashes.

**On Plus users:**
- Same as above, plus Apple/Google subscription status (which we receive from the App Store / Play Store, not stored alongside anything sensitive).

**We do NOT collect:**
- Location.
- Contacts.
- Health data beyond what you tell us (e.g. "drink water" is a habit name, not a Healthkit pull).
- Advertising identifiers.

## Where the data lives

- **Primary database**: Postgres hosted on Fly.io in US-East.
- **Backups**: snapshots retained for 14 days, stored encrypted at rest.
- **App analytics**: we use PostHog self-hosted, also on Fly.io. Event data is scoped to usage events (screen opens, feature usage) and does not include habit content.

Nothing goes to Facebook, Google Analytics, or any third-party ad network.

## Exporting your data

Settings → Data → **Export my data**. You'll get a ZIP file by email within 15 minutes containing:

- `habits.csv` — every habit you've ever created.
- `completions.csv` — every day/habit mark.
- `account.json` — non-sensitive account info.

No export format is proprietary; CSV and JSON open in any tool.

## Deleting your account

Settings → Account → **Delete account**. You'll be asked to confirm by typing your email. After confirmation:

- Your account is deleted immediately from the live database.
- Backups containing your data age out within 14 days.
- If you had Plus, the subscription continues until its end date (Apple/Google don't let us cancel it; you must from the App Store / Play Store).

**Deletion is permanent.** We can't restore an account after the 14-day backup window. If you want to take a break, consider signing out rather than deleting.

## GDPR / data-subject requests

EU users have the right to access, correct, and delete their data. The in-app export and delete flows handle these. For anything more complex (a specific date range, a particular field), email `privacy@streakly.app` and a human will respond within 30 days.

## Children under 13

Streakly is not designed for children under 13. If we discover an account belongs to a child under 13, we delete it. If you're a parent and you find your child has signed up, email `privacy@streakly.app` and we'll delete the account within 48 hours.

## Security

Passwords are hashed with `argon2`. Sessions are signed tokens that expire after 30 days of inactivity. We offer optional 2FA via TOTP apps (Authenticator, 1Password, etc.).

See `account-security.md` for what to do if you suspect your account has been compromised.
