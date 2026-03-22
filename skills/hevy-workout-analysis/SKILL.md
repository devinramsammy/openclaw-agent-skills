---
name: hevy-workout-analysis
description: For each exercise in the user's latest workout, fetches the last 5 times that exercise was performed (across any session) to identify per-exercise trends. After running the script, the response must cover every exercise in order with concrete next-session steps. Use when the user asks about their latest workout, progression on specific exercises, improvement, or wants fitness feedback with actionable plans per lift.
---

# Hevy Workout Analysis

For each exercise in the latest workout, look up the last 5 times it was performed across any session, then generate honest, personalized feedback on per-exercise trends.

## Setup

**If `.venv` does not exist** — create, activate, and install:

```bash
cd $HOME/.openclaw/skills/hevy-workout-analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**If `.venv` already exists** — activate only:

```bash
cd $HOME/.openclaw/skills/hevy-workout-analysis
source .venv/bin/activate
```

## Run

```bash
$HOME/.openclaw/skills/hevy-workout-analysis/.venv/bin/python3 \
  $HOME/.openclaw/skills/hevy-workout-analysis/scripts/analyze_workout.py
```

### Optional flags

| Flag        | Description                                      |
| ----------- | ------------------------------------------------ |
| `--index N` | Analyze the Nth most recent workout (0 = latest) |

## Output from script

Tracks each exercise independently across sessions — so alternating splits (Upper A/B/C, Push/Pull/Legs, etc.) are handled correctly. Bench Press history spans all workouts that included Bench Press, regardless of session name. All weights in **lbs**.

```json
{
  "latest_title": "Afternoon workout 💪",
  "latest_date": "Jan 15 2026",
  "unit": "lbs",
  "exercises": [
    {
      "name": "Bench Press",
      "sessions": [
        {
          "date": "Jan 15 2026",
          "sets": "4x8 @ 176.4lbs",
          "volume_lbs": 5645.9
        },
        {
          "date": "Jan 08 2026",
          "sets": "4x8 @ 176.4lbs",
          "volume_lbs": 5645.9
        },
        {
          "date": "Jan 01 2026",
          "sets": "4x8 @ 170.9lbs",
          "volume_lbs": 5469.3
        },
        {
          "date": "Dec 25 2025",
          "sets": "4x8 @ 170.9lbs",
          "volume_lbs": 5469.3
        },
        {
          "date": "Dec 18 2025",
          "sets": "3x8 @ 170.9lbs",
          "volume_lbs": 4102.0
        }
      ],
      "trend": "improving",
      "overall_volume_change_pct": 37.6
    },
    {
      "name": "Overhead Press",
      "sessions": [
        {
          "date": "Jan 15 2026",
          "sets": "3x10 @ 110.2lbs",
          "volume_lbs": 3306.0
        },
        {
          "date": "Jan 10 2026",
          "sets": "3x10 @ 110.2lbs",
          "volume_lbs": 3306.0
        },
        {
          "date": "Jan 03 2026",
          "sets": "3x10 @ 110.2lbs",
          "volume_lbs": 3306.0
        }
      ],
      "trend": "stagnant",
      "overall_volume_change_pct": 0.0
    }
  ]
}
```

`sessions` is ordered newest → oldest (up to 5). `trend` values: `improving`, `stagnant`, `declining`, `mixed`, `insufficient_data`.

## Output to the user (required template)

Interpret the JSON and write the reply **in this structure**. The model doing the analysis must follow it so nothing is skipped and every movement gets a plan.

**Coverage rule:** You must produce **one subsection per exercise** in `exercises`, in the **same order** as the array (that order matches the workout). Do not merge exercises, do not summarize “the rest,” and do not skip warm-ups or accessories if they appear as separate entries.

For **each** exercise, use this pattern (repeat for all):

### `<Exercise name>`

- **What the data shows** — 1–3 sentences grounded in `sessions`: dates, set/rep strings, volumes, and `trend` / `overall_volume_change_pct` when present. If `trend` is `insufficient_data` or there is only one session, say that plainly (e.g. first logged appearance or not enough history).
- **Next session (concrete)** — Specific actions for the **next** time they do this lift: target load (lbs), reps/sets, or a progression rule (e.g. “add 5 lbs if last week was clean,” “same weight, add one rep on the last set,” “one heavier top set + back-off,” “deload 10% if joints feel off”). Tie the advice to the trend (progress when improving, break plateaus when stagnant, protect volume or investigate fatigue when declining).

After all exercises:

### Workout recap

- **One paragraph** — Honest read on the session as a whole (not a repeat of every exercise).

**Tone:** Direct, like a knowledgeable training partner. Use real numbers and dates from the JSON. No filler, no generic praise without a per-exercise next step.

## Constraints

- Each exercise is tracked independently — no session-level matching needed
- Weights are always in lbs — do not convert
- If `sessions` has only 1 entry, note it's the first recorded instance of that exercise (still give a sensible **Next session** suggestion, e.g. repeat for technique or small progression)
- If the script returns an `error` key, report it clearly and stop
