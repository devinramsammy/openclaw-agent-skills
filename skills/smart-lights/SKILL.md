---
name: smart-lights
description: Turn lights and plugs on or off, and change light brightness. Use when the user wants to control lights (on/off, dim, brightness) or turn plugs or sockets on or off.
---

# Smart lights and plugs

Control lights (on/off, brightness) and plugs (on/off) via the Govee Open API. The API key and dependencies are already configured.

## Output

When reporting control results, respond with **only** a table of devices and the action taken. No extra explanation or commentary.

Example:

| Device       | Action         |
| ------------ | -------------- |
| Living Room  | on             |
| Bedroom Lamp | brightness 50% |

## Installation

Use a Python virtual environment when installing packages.

**If `.venv` already exists:** just activate it:

```bash
cd skills/smart-lights
source .venv/bin/activate
```

**If not:** create it, then activate and install:

```bash
cd skills/smart-lights
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Device list

Before controlling any device, you need the device list. It is cached at `./devices.json` in this skill directory.

**First time or if the user says "regenerate the list":**

```bash
python ./scripts/govee_client.py devices > ./devices.json
```

**All subsequent requests:** read `./devices.json` directly — do **not** call the API again unless the user explicitly asks to regenerate.

Each entry in the JSON has:

- `sku` — device model
- `device` — device id
- `deviceName` — human-readable name

Use `sku` and `device` for all control commands.

## Control commands

```bash
# On/off (lights and plugs)
python ./scripts/govee_client.py on <sku> <device>
python ./scripts/govee_client.py off <sku> <device>

# Brightness 1–100 (lights only)
python ./scripts/govee_client.py brightness <sku> <device> <percent>
```

### Get device state

```bash
python ./scripts/govee_client.py state <sku> <device>
```

Returns current state (on/off, brightness, etc.) in `payload.capabilities[]`.

## Module API

```python
from govee_client import (
    get_devices,
    get_device_state,
    control_device,
    turn_on,
    turn_off,
    set_brightness,
)
```

- **get_devices()** → full device list with capabilities.
- **get_device_state(sku, device)** → current state.
- **control_device(sku, device, capability_type, instance, value)** → send any command.
- **turn_on(sku, device)** / **turn_off(sku, device)** — works for lights and plugs.
- **set_brightness(sku, device, 1–100)**

## Capability reference

Get exact `type`, `instance`, and `value` options from `devices.json` → `capabilities[]` for each device.

| Capability type             | Instance    | Value           |
| --------------------------- | ----------- | --------------- |
| devices.capabilities.on_off | powerSwitch | 0 = off, 1 = on |
| devices.capabilities.range  | brightness  | 1–100           |

## API limits and errors

- **429** — rate limit (10,000 requests/account/day).
- **401** — invalid or missing API key.
- **404** — device or instance not found; confirm `sku`/`device` from `devices.json`.
