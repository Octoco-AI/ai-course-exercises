# When habits don't sync across devices

Sync is a Plus feature. If you're on Free, habits don't sync — that's expected, not a bug. See `billing-and-plans.md` for upgrading.

## How sync should work

When sync is working, a habit completion on your phone shows up on your tablet within about 30 seconds (when both are online). An edit on either side takes the same path.

## Basic troubleshooting (works in most cases)

1. **Check you're signed in on both devices** with the same account. Settings → Account → look at the email address. If they differ, you have two different accounts — we can't merge them automatically.

2. **Pull to refresh.** On the habit list, pull down. This forces a sync pull.

3. **Check internet.** Sync needs both devices to be online. Airplane mode disables sync entirely.

4. **Confirm Plus is active on both devices.** Settings → Streakly Plus → should say "Active" on both.

## If a specific habit isn't syncing

Some edge cases:

- **You created the habit while offline on the tablet, and it hasn't come back online since.** That habit exists only on the tablet. Bring it online; it'll upload to the server and appear on other devices.

- **Conflict**: you edited the same habit on two devices without reconnecting. We use "last write wins" — the most recent edit takes precedence. If the "wrong" edit won, you can re-apply the right one now.

- **Habit deleted on one device.** Deletions propagate; the habit will disappear on the other device once it syncs. If you deleted by accident and want to recover, see `contacting-support.md` — we can usually restore within 14 days.

## If nothing syncs on a particular device

1. **Sign out and back in** on that device.
2. **Check the sync indicator** — Settings → Sync → Status. Should say "Connected, last sync at: XX:XX". If it says "Error: ...", the message explains what's wrong.
3. **Check for app updates.** Occasionally we fix sync bugs; running an old app version can prevent sync until you update.
4. **Delete and reinstall the app as a last resort.** Your data is on the server; reinstalling pulls it fresh.

## Sync shows an error message

Common messages and their causes:

- **"Sign in again"**: your session expired. Sign out and back in.
- **"Subscription inactive"**: the Plus subscription lapsed or wasn't detected. Try **Restore purchases** under Streakly Plus.
- **"Server unreachable"**: network or Streakly's servers. Check [status.streakly.app](https://status.streakly.app) — if we're down, you'll see it there.
- **"Too many conflicts"**: if you've been offline on two devices for a long time with many edits, we sometimes pause sync to let you resolve conflicts manually. Tap the message; it takes you to the resolution view.

## Still not syncing

Contact support. Include:

- Both device types and OS versions.
- The specific habit (or habits) affected.
- When you last saw sync working correctly.
- A screenshot of the sync status screen from each device.

We can usually diagnose from that within a few hours.
