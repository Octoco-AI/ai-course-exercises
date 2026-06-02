# How streaks work

## The basic rule

A **streak** is the number of consecutive days you marked a habit done.

- Mark done today → streak grows by 1.
- Miss a day → streak resets to 0.
- Mark done again → streak starts over at 1.

Each habit has its own streak. You can have a 30-day streak on "drink water" and a fresh 1-day streak on "journal".

## Timezone handling

We use your device's local timezone to decide when "today" ends. Midnight local time = day rollover.

If you travel across timezones, your day can be longer or shorter. We've chosen not to make this clever — the trade-off between "sometimes you get a free day" and "sometimes you lose one" is fair over time, and clever logic around this confused more users than it helped.

## Streak Recovery (Plus only)

Plus subscribers get **Streak Recovery** — miss one day per month without losing your streak.

You don't have to do anything to activate it. If you miss a day and you have Recovery available, the app shows "Streak recovered — you're back on!" the next time you open it.

One Recovery per calendar month, per habit. Recovery doesn't stack; you can't save up two months' recoveries for a bigger break.

## Partial completions

Streakly supports two kinds of habit:

**Binary habits** (the default): marked as done or not.

**Count habits**: you enter a number. Each count habit has a daily goal. If you meet or exceed the goal, the day counts; if not, it doesn't. Partial counts are saved for your insights but don't contribute to the streak.

## Editing past days

You can edit the **last 7 days** — useful if you forgot to mark a day done. Tap the day in the grid view, then **Mark done** or **Clear**. Beyond 7 days you're stuck with history as-is; we chose this to prevent rewriting streaks retroactively.

## My streak looks wrong

Most commonly:

1. **You travelled timezones.** Day boundaries changed; the app may show a gap that feels unfair. Use the edit-past-days feature within 7 days to correct.
2. **Daylight-saving transitions.** On DST days the local day is 23 or 25 hours. We honour whatever your device thinks is "today"; clock weirdness usually resolves once DST stabilises.
3. **Free-plan sync.** On Free, habits are stored locally. If you used the app on two devices without Plus, each has its own streak. Upgrade to Plus to merge them (we take the higher streak).
4. **You actually missed a day.** Streak reset. Sorry — the Recovery feature on Plus exists for exactly this case.

If none of the above fit, contact support with the habit name and approximate dates — we can look at your device logs if you share them.
