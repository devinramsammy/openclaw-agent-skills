---
name: scheduling-sunset-lights
description: Runs a script to schedule today's smart-lights cron job 20 minutes before NYC sunset. Use when asked to "trigger sunset-lights", refresh the sunset schedule, or set up the daily sunset automation. Does NOT directly control lights — only schedules the one-shot cron job.
---

# Scheduling Sunset Lights

Runs `schedule_sunset_lights.py` to fetch today's NYC sunset from Open-Meteo, subtract 20 minutes, and register/replace an OpenClaw one-shot cron job (`sunset-lights-job`) that fires at that time.

**This skill only schedules the cron job. It does not control lights directly.** Light control happens later via the smart-lights skill when the one-shot job fires.

## Prerequisites

- The smart-lights skill must be set up for the one-shot job to act on the event.

## Setup

**If `.venv` already exists:** skip this.

**If not:**

```bash
cd skills/sunset-lights
python -m venv .venv
source .venv/bin/activate
pip install requests
```

## Run

Always run this script — do not attempt to toggle lights directly:

```bash
skills/sunset-lights/.venv/bin/python skills/sunset-lights/scripts/schedule_sunset_lights.py
```

Removes any existing `sunset-lights-job`, then registers a new one-shot job firing at sunset − 20 min today.
