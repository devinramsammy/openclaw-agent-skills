#!/usr/bin/env python3
"""
Fetch today's NYC sunset from Open-Meteo, subtract 20 minutes,
then register/replace an OpenClaw one-shot cron job to turn on all smart lights at that time.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=40.7128&longitude=-74.0060"
    "&daily=sunset&timezone=America%2FNew_York"
)

# Open-Meteo is a lightweight public JSON API; 10s is generous for a single daily response
REQUEST_TIMEOUT = 10

# Lights turn on this many minutes before sunset
SUNSET_OFFSET_MINUTES = 20

JOB_NAME = "sunset-lights-job"
SYSTEM_EVENT_TEXT = "Turn on all lights now"


def fetch_sunset() -> datetime:
    try:
        resp = requests.get(OPEN_METEO_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: Could not fetch sunset data: {exc}", file=sys.stderr)
        print("Check your internet connection and retry.", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    # API returns e.g. "2026-02-26T17:28" in America/New_York; treat as local NYC time
    sunset_str = data["daily"]["sunset"][0]
    return datetime.fromisoformat(sunset_str)


def openclaw(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["openclaw", *args]
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=not capture,
    )


def remove_existing_job() -> None:
    """Remove any existing OpenClaw cron job named JOB_NAME."""
    result = openclaw("cron", "list", "--json", capture=True)
    if result.returncode != 0 or not result.stdout.strip():
        return

    try:
        jobs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return

    for job in jobs:
        if job.get("name") == JOB_NAME:
            job_id = job.get("jobId") or job.get("id")
            if job_id:
                openclaw("cron", "remove", job_id)
                print(f"Removed existing OpenClaw cron job: {job_id}")


def register_cron_job(trigger_time: datetime) -> None:
    """Register a one-shot OpenClaw cron job for trigger_time (NYC local, naive)."""
    # Convert naive NYC local time to UTC ISO 8601 for OpenClaw
    nyc_offset = timedelta(hours=-5)  # EST; Open-Meteo returns standard/local correctly
    trigger_utc = trigger_time.replace(tzinfo=timezone(nyc_offset)).astimezone(timezone.utc)
    at_iso = trigger_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    remove_existing_job()

    openclaw(
        "cron", "add",
        "--name", JOB_NAME,
        "--at", at_iso,
        "--session", "main",
        "--system-event", SYSTEM_EVENT_TEXT,
        "--wake", "now",
        "--delete-after-run",
    )

    print(
        f"OpenClaw cron job registered: lights on at "
        f"{trigger_time.strftime('%H:%M')} NYC "
        f"(= {trigger_utc.strftime('%H:%M')} UTC, sunset − {SUNSET_OFFSET_MINUTES} min)"
    )


def main() -> None:
    print("Fetching NYC sunset time from Open-Meteo...")
    sunset = fetch_sunset()
    trigger = sunset - timedelta(minutes=SUNSET_OFFSET_MINUTES)

    print(f"Sunset : {sunset.strftime('%H:%M')} NYC")
    print(f"Trigger: {trigger.strftime('%H:%M')} NYC (sunset − {SUNSET_OFFSET_MINUTES} min)")

    register_cron_job(trigger)


if __name__ == "__main__":
    main()
