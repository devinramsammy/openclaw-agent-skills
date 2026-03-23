---
name: catch-corner-tennis
description: Fetches NYC tennis court rental availability from Catch Corner for Cunningham, Alley Pond, and McCarren tennis. Use when the user asks about tennis court times, Cunningham Tennis, Alley Pond Tennis, McCarren Tennis, or NYC public tennis rental availability.
---

# Catch Corner tennis availability

## Setup

**If `.venv` does not exist** — create, activate, and install:

```bash
cd $HOME/.openclaw/skills/catch-corner-tennis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**If `.venv` already exists** — invoke via the venv interpreter:

```bash
$HOME/.openclaw/skills/catch-corner-tennis/.venv/bin/python3 \
  $HOME/.openclaw/skills/catch-corner-tennis/scripts/fetch_tennis_availability.py --help
```

## Arenas

| Arena ID | Name              |
| -------- | ----------------- |
| 1253     | Cunningham Tennis |
| 922      | Alley Pond Tennis |
| 1039     | McCarren Tennis   |

Aliases: `cunningham` → 1253, `alley-pond` / `alleypond` → 922, `mccarren` / `mccarren-tennis` → 1039, `both` / `all` → fetch all three.

## Weeks and time

- The script loads data in **UTC week** slices (Sunday `00:00` UTC through the next Sunday `00:00` UTC). Map “this week” / ranges to `--week-start` or `--from` / `--to` accordingly.
- **Output** is **compact Eastern** (America/New_York): short weekday + month + day (`Mon Mar 23`), then one line per venue with **comma-separated** ranges like `9:30 AM – 1 PM` (no “Tennis” in names).

## Filter range (optional)

Use `--filter-from` and `--filter-to` together to keep only slots that **overlap** that window (`slot_start < filter_end` and `slot_end > filter_start`).

## Resolve “today” from the system

For “this week” / “next week”, use the real clock, not chat context:

```bash
date -u +%Y-%m-%d
```

or rely on the script default (current UTC week when no range is passed).

## Run the script

```bash
$HOME/.openclaw/skills/catch-corner-tennis/.venv/bin/python3 \
  $HOME/.openclaw/skills/catch-corner-tennis/scripts/fetch_tennis_availability.py \
  --arena <arena> \
  [--week-start YYYY-MM-DD | --from ISO8601 --to ISO8601] \
  [--filter-from ISO8601 --filter-to ISO8601]
```

- **`--week-start`**: one UTC week containing that date.
- **`--from` / `--to`**: all overlapping UTC weeks in that range (both required together).
- If neither: **current UTC week**.
- **`--filter-from` / `--filter-to`**: optional; both required together.

## Output

The script prints **only** a **plain-text list**: compact day headers, then `Venue: range, range, …` (short venue names, 12-hour times with **AM** / **PM**).

**Reply with exactly that list** — paste the script stdout into **one fenced code block** (triple backticks). Do **not** add a “Notes” section, bullets, explanations, or any text before or after the block unless the user asks. Do **not** output JSON.

Example shape (script stdout only):

````markdown
```
Mon Mar 23
Alley Pond: 9:30 AM – 1 PM, 1:30 PM – 4:30 PM, 9 PM – 10 PM
Cunningham: 2 PM – 3 PM, 11 PM – 12 AM

Tue Mar 24
Cunningham: 6 AM – 7:30 AM, 3 PM – 5 PM, 10 PM – 12 AM
Alley Pond: 8 AM – 7 PM
```
````
