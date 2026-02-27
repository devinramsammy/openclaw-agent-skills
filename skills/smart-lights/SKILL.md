---
name: smart-lights
description: Control smart lights and plugs via the Govee API — turn on/off, set brightness, and query device state. Use when the user wants to control lights (on/off, dim, brightness), turn plugs or sockets on or off, or check the current state of a device.
---

# Smart lights and plugs

Control lights (on/off, brightness) and plugs (on/off) via the Govee Open API. The API key and dependencies are already configured.

## Output

When reporting control results, respond with **only** a table of devices and the action taken. No extra explanation or commentary.

| Device       | Action         |
| ------------ | -------------- |
| Living Room  | on             |
| Bedroom Lamp | brightness 50% |

## Setup

All commands run from the `skills/smart-lights` directory. Activate the virtual environment first:

**If `.venv` already exists:**

```bash
cd skills/smart-lights && source .venv/bin/activate
```

**If not:**

```bash
cd skills/smart-lights
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Device list

Device info is cached at `./devices.json`. Each entry has `sku` (model), `device` (id), and `deviceName`.

**First time or if the user says "regenerate the list":**

```bash
python ./scripts/govee_client.py devices > ./devices.json
```

**All subsequent requests:** read `./devices.json` directly — do **not** call the API again unless asked.

## Control commands

```bash
# On/off (lights and plugs)
python ./scripts/govee_client.py on <sku> <device>
python ./scripts/govee_client.py off <sku> <device>

# Brightness 1–100 (lights only)
python ./scripts/govee_client.py brightness <sku> <device> <percent>

# Query current state
python ./scripts/govee_client.py state <sku> <device>
```

`state` returns current on/off, brightness, etc. in `payload.capabilities[]`.

## API limits and errors

- **429** — rate limit (10,000 requests/account/day).
- **401** — invalid or missing API key.
- **404** — device or instance not found; confirm `sku`/`device` from `devices.json`.
