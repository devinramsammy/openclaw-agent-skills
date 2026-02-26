---
name: manage-calendar
description: Use when the user asks to add, create, or schedule an event; modify, change, or reschedule an event; check their schedule or agenda; find free time or availability; or asks when would be a good time to do something.
---

# Manage Calendar

## Setup

Use a Python virtual environment when installing packages.

**If `.venv` already exists:** just activate it:

```bash
cd skills/manage-calendar
source .venv/bin/activate
```

**If not:** create it, then activate and install:

```bash
cd skills/manage-calendar
python -m venv .venv
source .venv/bin/activate
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

`credentials.json` must be present in `skills/manage-calendar/`. On first run a browser window opens for OAuth consent — `token.json` is saved automatically after.

## Workflow

### 1. Parse intent

| User intent                      | Command                              |
| -------------------------------- | ------------------------------------ |
| View schedule / daily agenda     | `list`                               |
| Add / create / schedule event    | `add`                                |
| Change / move / reschedule event | `modify` (search first for event ID) |
| Find free time / availability    | `free`                               |
| Find a specific event            | `search`                             |

### 2. Resolve "today" from the system

**Source of truth for "today":** Run the system date command — do not use the date from conversation/system context (it can be wrong).

```bash
date +%Y-%m-%d
```

Use that output for "today". For "tomorrow", add one day; for other relative dates, compute from this date.

### 3. Extract entities

Resolve relative terms from the **today** value you obtained above. Never use example years from this document (e.g. 2025, 2026) literally.

- **Date** → `YYYY-MM-DD` using the **current calendar year** and the system-derived today ("tomorrow", "this Saturday", "next Monday"). If the user says "today" or "my schedule", use the date from `date +%Y-%m-%d`.
- **Time** → 24h ISO with local timezone offset ("3pm" → `T15:00:00-05:00`)
- **Duration** → compute end time from start + duration ("for an hour" → `+1:00:00`)
- **Title** → clean event name ("ryans birthday party" → "Ryan's Birthday Party")

### 4. Run script

All commands run from the workspace root using the `.venv` interpreter:

**View schedule:**

```bash
skills/manage-calendar/.venv/bin/python skills/manage-calendar/scripts/calendar_ops.py list --date YYYY-MM-DD [--days N]
```

**Add event:**

```bash
skills/manage-calendar/.venv/bin/python skills/manage-calendar/scripts/calendar_ops.py add \
  --title "Ryan's Birthday Party" \
  --start "YYYY-MM-DDTHH:MM:SS±HH:MM" \
  --end   "YYYY-MM-DDTHH:MM:SS±HH:MM" \
  [--description "..."] [--location "..."]
```

**Modify event** — run `search` first to get the event ID:

```bash
skills/manage-calendar/.venv/bin/python skills/manage-calendar/scripts/calendar_ops.py search --query "dentist" [--days 30]

skills/manage-calendar/.venv/bin/python skills/manage-calendar/scripts/calendar_ops.py modify \
  --event-id EVENT_ID \
  [--title "..."] [--start "..."] [--end "..."] [--description "..."] [--location "..."]
```

**Find free time:**

```bash
skills/manage-calendar/.venv/bin/python skills/manage-calendar/scripts/calendar_ops.py free \
  --date YYYY-MM-DD \
  --duration 60 \
  [--range-start 06:00] [--range-end 22:00]
```

### 5. Format response

**Schedule (list):**

```
📅 Friday, Feb 27
─────────────────────────
 9:00 AM  Team standup (30 min)
11:00 AM  Lunch with Sarah — Nobu
 3:00 PM  Dentist appointment (1 hr)
```

If no events: "You have nothing scheduled."

**Add / modify confirmation:**

```
✅ Added: Ryan's Birthday Party
   Saturday, Mar 1 · 3:00–4:00 PM
```

**Free time (with activity suggestion):**

```
Free slots tomorrow with 60+ min available:
• 7:00–9:00 AM   (2h) ← ideal for gym
• 1:00–3:00 PM   (2h)
• 8:00–10:00 PM  (2h)
```

When recommending times for a specific activity, apply judgment:

- **Gym / workout** → early morning (6–9 AM) or evening (6–9 PM)
- **Focused work** → morning blocks
- **Social / meals** → midday or evening
- Prefer slots with buffer around existing events

## Rules

- For `modify`, always run `search` first — never guess an event ID
- If key details are ambiguous (date, time), ask before executing
- **Date resolution:** Always get **today** by running `date +%Y-%m-%d` (system date). Use that for "today", and derive "tomorrow" and other relative dates from it. Never use conversation context or example years from this document.
- On `add`/`modify` success, show the confirmed event details
