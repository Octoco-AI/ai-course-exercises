# Plan/Execute Split — Module 7

A runnable version of the **M7 cost-comparison exercise**. Run the same task two
ways on Google Gemini — **Flash monolithic** vs. **Pro-plan + Flash-execute** —
and read the actual dollar numbers.

**You do not need to know Python.** Edit one plain-text file (`task.md`), run
three commands, and the scripts print token counts, dollar cost, and wall-clock
time and append them to `COMPARISON.md` for you.

> Free Gemini tier? Your real spend is likely **$0**. The dollar figures the
> scripts print are token counts × list price — that's the comparison that
> matters, not your bill.

---

## Setup (5 minutes, before the workshop)

1. **Python 3.12 or later** — check with `python3 --version`.
2. **A free Gemini API key** — [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
3. **Install the two dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install google-genai python-dotenv
   ```
4. **Add your key:**
   ```bash
   cp .env.example .env
   # open .env and paste your key into GOOGLE_API_KEY
   ```
5. **Verify everything works:**
   ```bash
   ./verify.sh
   ```

---

## The one file you edit: `task.md`

`task.md` is plain text (Markdown). Replace its contents with your task — what
"done" looks like, acceptance criteria, file paths, and any "never do this"
constraints. All three scripts read this same file.

It ships with the **fallback task** (add a `GET /categories/top` endpoint to the
expense-categoriser), which runs out of the box against the default workspace —
so you can do a full dry run before swapping in your own task.

### Where the agent makes its edits: `WORKSPACE`

The agent reads and edits files inside the directory named by `WORKSPACE` in
`.env`. It is sandboxed there — it cannot touch the rest of your machine.

- **Default:** `../expense-categoriser` (the sibling exercise), so the fallback
  task works immediately. The agent will modify those files — reset them
  afterwards with `git checkout -- .` inside that directory, or work on a copy.
- **Your own task:** set `WORKSPACE` to an absolute path to your repo, e.g.
  `WORKSPACE=/Users/you/code/your-project`. Best on a scratch branch so you can
  throw the agent's edits away.

---

## Run it (the exercise)

Pair up. **Partner A** runs the monolithic baseline; **Partner B** runs the
split. Don't compare until both finish.

### Partner A — Flash monolithic (one call, budget tier)
```bash
python run_monolithic.py
```

### Partner B — Pro plans, then Flash executes (two calls)
```bash
python run_plan.py      # Gemini 3.1 Pro writes plan.md (read it!)
python run_execute.py   # Gemini 3.1 Flash-Lite implements plan.md
```

Each script prints a summary and appends a section to `COMPARISON.md`:

```
  ── Flash monolithic ──
  Model:         gemini-3.1-flash-lite
  Input tokens:  4182
  Output tokens: 1530 (+0 thinking)
  Approx cost:   $0.0051
  Wall-clock:    8.3s
  → appended to COMPARISON.md
```

Fill in the **Quality** lines in `COMPARISON.md` by hand (tests pass? spec met?
manual fixes needed?) — that's the half of the comparison the scripts can't
measure.

---

## Read the result

Open `COMPARISON.md`. You'll have three sections: *Flash monolithic*,
*Plan (Pro)*, and *Execute (Flash)*. Then, together:

- **Split total** = Plan cost + Execute cost.
- **Cost ratio** = split total ÷ Flash-Lite monolithic. (The split usually costs
  **more** than the budget tier alone — 2×–5×. The comparison that matters is
  split vs. **Pro monolithic**.)
- **Pro monolithic (estimated)** = re-price the monolithic token counts at Pro
  rates ($2 in / $12 out). The split typically lands at ~1/2 of that on Gemini;
  on the Anthropic path the split is ~1/6 of Opus monolithic.
- **Quality delta** — which output was better, and on what axis?

Then write the one decision that matters: *for tasks of this shape in my real
backlog, would I use the split?*

---

## Tuning

- **Wider price gap on execution.** Set `EXECUTOR_MODEL=gemini-3.1-flash-lite`
  in `.env` — the ultra-budget tier. The report prices it automatically.
- **Better plans.** Edit `PLANNER_PROMPT` at the top of `run_plan.py` (it's
  clearly marked) and re-run. The planner prompt is where teams compound gains
  over the first month — a 10-minute investment pays off every later run.

---

## What lives where

```
plan-execute-split/
├── README.md          ← you are here
├── task.md            ← THE ONLY FILE YOU EDIT (your task)
├── .env.example       ← copy to .env, add your key + WORKSPACE
├── verify.sh          ← pre-flight check
├── run_monolithic.py  ← Partner A: Flash, one call
├── run_plan.py        ← Partner B step 1: Pro writes plan.md
├── run_execute.py     ← Partner B step 2: Flash implements plan.md
├── agent.py           ← shared agent loop (sums token usage across turns)
├── tools.py           ← the 3 file tools, sandboxed to WORKSPACE
├── pricing.py         ← price table + cost maths + COMPARISON.md writer
├── plan.md            ← generated by run_plan.py
└── COMPARISON.md      ← generated; your two runs land here
```

You only ever edit `task.md` and `.env`. The other files are the machinery —
peek at them if you're curious; they're short and commented.

---

## On Claude instead of Gemini?

This pack is the Gemini path. The shape is identical on Anthropic — Opus 4.8
plans, Haiku 4.5 executes. The M7 exercise instructions include the Anthropic
code in collapsible blocks. Swap `pip install anthropic`, an `ANTHROPIC_API_KEY`,
and Claude's `tool_use` content blocks for Gemini's `function_call` parts.
