---
name: scheduling-sunset-lights
description: Schedules smart lights to turn on 20 minutes before NYC sunset via an OpenClaw cron job. Use when the user wants to automate lights at sunset or refresh today's sunset trigger time.
---

# Scheduling Sunset Lights

Fetches today's NYC sunset from Open-Meteo (no API key needed), subtracts 20 minutes, and registers/replaces an OpenClaw one-shot cron job to fire a main-session system event at that time. The agent then turns on all smart lights when the event fires.

## Prerequisites

- The smart-lights skill must be fully set up so the agent can act on the system event.

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

```bash
skills/sunset-lights/.venv/bin/python skills/sunset-lights/scripts/schedule_sunset_lights.py
```

Removes any existing OpenClaw cron job named `sunset-lights-job`, then registers a new one-shot job firing at sunset − 20 min today.
