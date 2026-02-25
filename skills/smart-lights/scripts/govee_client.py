#!/usr/bin/env python3
"""
Smart lights/plugs API client (Govee Open API) using HTTP requests.
API key is read from GOVEE_API_KEY (environment or .env in the skill directory).

References:
- https://developer.govee.com/reference/get-you-devices
- https://developer.govee.com/reference/control-you-devices
- https://developer.govee.com/reference/get-devices-status
- https://developer.govee.com/reference/get-light-scene
"""

import os
import uuid
import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import requests
except ImportError:
    print(
        json.dumps({"error": "Install requests: pip install requests"}),
        file=sys.stderr,
    )
    sys.exit(1)

BASE_URL = "https://openapi.api.govee.com"
ENV_API_KEY = "GOVEE_API_KEY"

# .env is loaded from the skill directory (e.g. skills/smart-lights/.env)
_SKILL_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Load .env from the skill directory if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_file = _SKILL_DIR / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass


def _get_api_key() -> str:
    _load_dotenv()
    key = os.environ.get(ENV_API_KEY)
    if not key or not key.strip():
        raise ValueError(
            f"Missing {ENV_API_KEY}. Set it in your environment or in {_SKILL_DIR / '.env'}"
        )
    return key.strip()


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Govee-API-Key": _get_api_key(),
    }


def _request_id() -> str:
    return str(uuid.uuid4())


def get_devices() -> dict[str, Any]:
    """
    GET /router/api/v1/user/devices
    Returns list of devices with sku, device id, deviceName, and capabilities.
    """
    r = requests.get(
        f"{BASE_URL}/router/api/v1/user/devices",
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_device_state(sku: str, device: str) -> dict[str, Any]:
    """
    POST /router/api/v1/device/state
    Returns current state (e.g. on/off, brightness, color) for the device.
    """
    r = requests.post(
        f"{BASE_URL}/router/api/v1/device/state",
        headers=_headers(),
        json={
            "requestId": _request_id(),
            "payload": {"sku": sku, "device": device},
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def control_device(
    sku: str,
    device: str,
    capability_type: str,
    instance: str,
    value: Any,
) -> dict[str, Any]:
    """
    POST /router/api/v1/device/control
    Send a control command. value can be int, str, or dict depending on capability.

    Common capabilities:
    - devices.capabilities.on_off, instance powerSwitch, value 0|1 (off|on)
    - devices.capabilities.range, instance brightness, value 1-100
    - devices.capabilities.color_setting, instance colorRgb, value 0-16777215 (RGB as int)
    - devices.capabilities.color_setting, instance colorTemperatureK, value 2000-9000
    - devices.capabilities.toggle, instance gradientToggle, value 0|1
    - devices.capabilities.mode, instance nightlightScene, value from device options
    - devices.capabilities.dynamic_scene, instance lightScene, value (int or {paramId, id} for dynamic)
    """
    r = requests.post(
        f"{BASE_URL}/router/api/v1/device/control",
        headers=_headers(),
        json={
            "requestId": _request_id(),
            "payload": {
                "sku": sku,
                "device": device,
                "capability": {
                    "type": capability_type,
                    "instance": instance,
                    "value": value,
                },
            },
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_light_scenes(sku: str, device: str) -> dict[str, Any]:
    """
    POST /router/api/v1/device/scenes
    Returns dynamic light scene options for this device (e.g. Sunrise, Ocean).
    """
    r = requests.post(
        f"{BASE_URL}/router/api/v1/device/scenes",
        headers=_headers(),
        json={
            "requestId": _request_id(),
            "payload": {"sku": sku, "device": device},
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_diy_scenes(sku: str, device: str) -> dict[str, Any]:
    """
    POST /router/api/v1/device/diy-scenes
    Returns user-defined DIY scene options for this device.
    """
    r = requests.post(
        f"{BASE_URL}/router/api/v1/device/diy-scenes",
        headers=_headers(),
        json={
            "requestId": _request_id(),
            "payload": {"sku": sku, "device": device},
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# --- Helpers for common actions ---


def rgb_to_int(r: int, g: int, b: int) -> int:
    """Convert 0-255 R,G,B to Govee color integer (0-16777215)."""
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return (r << 16) | (g << 8) | b


def turn_on(sku: str, device: str) -> dict[str, Any]:
    return control_device(sku, device, "devices.capabilities.on_off", "powerSwitch", 1)


def turn_off(sku: str, device: str) -> dict[str, Any]:
    return control_device(sku, device, "devices.capabilities.on_off", "powerSwitch", 0)


def set_brightness(sku: str, device: str, percent: int) -> dict[str, Any]:
    percent = max(1, min(100, percent))
    return control_device(
        sku, device, "devices.capabilities.range", "brightness", percent
    )


def set_color_rgb(sku: str, device: str, r: int, g: int, b: int) -> dict[str, Any]:
    return control_device(
        sku,
        device,
        "devices.capabilities.color_setting",
        "colorRgb",
        rgb_to_int(r, g, b),
    )


def set_color_temperature_k(sku: str, device: str, kelvin: int) -> dict[str, Any]:
    kelvin = max(2000, min(9000, kelvin))
    return control_device(
        sku,
        device,
        "devices.capabilities.color_setting",
        "colorTemperatureK",
        kelvin,
    )


def main() -> None:
    """CLI: list devices by default; optional action with sku/device."""
    _load_dotenv()
    if not os.environ.get(ENV_API_KEY) or not os.environ.get(ENV_API_KEY).strip():
        print(f"Set {ENV_API_KEY} in the environment or in {_SKILL_DIR / '.env'}.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print(json.dumps(get_devices(), indent=2))
        return

    cmd = sys.argv[1].lower()
    if cmd == "devices" or cmd == "list":
        print(json.dumps(get_devices(), indent=2))
    elif cmd == "state" and len(sys.argv) >= 4:
        print(json.dumps(get_device_state(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "on" and len(sys.argv) >= 4:
        print(json.dumps(turn_on(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "off" and len(sys.argv) >= 4:
        print(json.dumps(turn_off(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "brightness" and len(sys.argv) >= 5:
        print(
            json.dumps(
                set_brightness(sys.argv[2], sys.argv[3], int(sys.argv[4])),
                indent=2,
            )
        )
    elif cmd == "scenes" and len(sys.argv) >= 4:
        print(json.dumps(get_light_scenes(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "diy-scenes" and len(sys.argv) >= 4:
        print(json.dumps(get_diy_scenes(sys.argv[2], sys.argv[3]), indent=2))
    else:
        print(
            "Usage: govee_client.py [devices|state SKU DEVICE|on SKU DEVICE|off SKU DEVICE|brightness SKU DEVICE 1-100|scenes SKU DEVICE|diy-scenes SKU DEVICE]",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
