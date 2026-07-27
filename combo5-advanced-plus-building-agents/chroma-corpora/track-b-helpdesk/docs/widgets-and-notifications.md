# Widgets and notifications

## Home-screen widgets (Plus only)

Streakly offers three widget sizes on both iOS and Android.

- **Small**: one habit, its current streak, and a tap-to-mark-done.
- **Medium**: up to 3 habits in a row.
- **Large**: a 7-day grid for a single habit.

### Adding a widget on iOS

Long-press the home screen → tap **+** (top-left) → search for "Streakly" → pick a size → **Add Widget**.

After adding, tap the widget to choose which habit it tracks. Widgets refresh approximately every 15 minutes — iOS controls the refresh cadence, not us.

### Adding a widget on Android

Long-press the home screen → **Widgets** → scroll to Streakly → drag a widget onto the screen. Tap to configure which habit it tracks.

### My widget is stuck or shows old data

iOS caches widget content aggressively. Usually one of:

1. **Wait 15 minutes.** iOS may not have refreshed it.
2. **Open the app.** Opening Streakly triggers an immediate widget refresh.
3. **Remove and re-add the widget.**
4. **Restart the phone.** Last resort; works surprisingly often.

If you've marked a habit done in the app but the widget still says it's not done after 30 minutes with the app opened, that's a bug — please contact support.

## Reminder notifications

Every habit can have reminders. **Settings → [habit name] → Reminders**.

Reminder options:

- **Time-based**: "every day at 8:00 AM".
- **After another habit**: "remind me 30 minutes after I mark 'morning run' done". Habit-chaining.
- **Snooze-based**: a sticky notification until you act. Only recommended for one habit at a time.

### Notifications aren't arriving

iOS and Android both have many layers where notifications can be blocked. Check each:

1. **App-level in Streakly**: Settings → Notifications → notifications **enabled**.
2. **Per-habit**: each habit's reminder must be **on**.
3. **OS-level**:
   - iOS: Settings → Notifications → Streakly → allow.
   - Android: Settings → Apps → Streakly → Notifications → allow.
4. **Do Not Disturb / Focus Mode**: if enabled for the reminder time, notifications are suppressed.
5. **Battery saver / Optimisation**: some Android manufacturers (Xiaomi, Huawei, Samsung) aggressively kill background apps. Streakly needs to be exempted. How-to differs by phone; search your phone model + "battery optimisation exceptions".

### I get duplicate reminders

Usually caused by having the app installed on two devices, each scheduling reminders locally. On Plus, sync means both devices know about the habit but each schedules its own local reminder. Turn off notifications on the device you don't want reminders from.

### Notifications are noisy / too many habits

A cheap fix: create one reminder called "Daily Streakly check" that opens the app, and disable the per-habit reminders. One notification, check everything at once.
