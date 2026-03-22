#!/usr/bin/env python3
"""
For each exercise in the most recent workout, fetch the last N times that exercise
was performed via the Hevy server APIs (no full-workout dump on the hot path).
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

BASE_URL = "https://hevy-docker-server-production.up.railway.app"
HISTORY_PER_EXERCISE = 5


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.setdefault("Accept", "application/json")
    return s


def fetch_latest_workout(session: requests.Session) -> Optional[dict]:
    try:
        resp = session.get(f"{BASE_URL}/workouts/latest", timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot reach the workout server.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Server returned {e.response.status_code}", file=sys.stderr)
        sys.exit(1)


def fetch_workouts_list(session: requests.Session) -> list[dict]:
    """Fallback when --index > 0: server has no offset endpoint."""
    try:
        resp = session.get(f"{BASE_URL}/workouts", timeout=30)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot reach the workout server.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Server returned {e.response.status_code}", file=sys.stderr)
        sys.exit(1)


def fetch_workout_at_index(session: requests.Session, index: int) -> Optional[dict]:
    if index == 0:
        return fetch_latest_workout(session)
    workouts = fetch_workouts_list(session)
    workouts.sort(
        key=lambda w: parse_time(w.get("start_time") or w.get("created_at")) or datetime.min,
        reverse=True,
    )
    if index >= len(workouts):
        return None
    return workouts[index]


def fetch_exercise_history(
    session: requests.Session,
    title: str,
    limit: int = HISTORY_PER_EXERCISE,
) -> Dict[str, Any]:
    encoded = quote(title, safe="")
    resp = session.get(
        f"{BASE_URL}/exercises/{encoded}/history",
        params={"limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def parse_time(t: Optional[str]) -> Optional[datetime]:
    if not t:
        return None
    try:
        return datetime.fromtimestamp(float(t))
    except (ValueError, OSError):
        pass
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None


def fmt_date_iso(iso: Optional[str]) -> str:
    t = parse_time(iso)
    return t.strftime("%b %d %Y") if t else "unknown date"


def fmt_date_workout(w: dict) -> str:
    return fmt_date_iso(w.get("start_time") or w.get("created_at"))


def to_lbs(kg: float) -> float:
    return round(kg * 2.20462, 2)


def sets_summary_lbs(sets: list[dict]) -> str:
    if not sets:
        return "no sets recorded"
    # Sort by set_index if present (API order is usually correct)
    ordered = sorted(sets, key=lambda s: s.get("set_index", s.get("index", 0)))
    groups: list[str] = []
    cw = ordered[0].get("weight_kg") or 0
    cr = ordered[0].get("reps") or 0
    count = 1
    for s in ordered[1:]:
        w = s.get("weight_kg") or 0
        r = s.get("reps") or 0
        if w == cw and r == cr:
            count += 1
        else:
            groups.append(f"{count}x{cr} @ {to_lbs(cw)}lbs")
            cw, cr, count = w, r, 1
    groups.append(f"{count}x{cr} @ {to_lbs(cw)}lbs")
    return ", ".join(groups)


def volume_lbs_from_sets(sets: list[dict]) -> float:
    total = 0.0
    for s in sets:
        total += (s.get("weight_kg") or 0.0) * (s.get("reps") or 0)
    return to_lbs(round(total, 2))


def trend_label(volumes: list[float]) -> str:
    if len(volumes) < 2:
        return "insufficient_data"
    oldest, newest = volumes[-1], volumes[0]
    if oldest == 0:
        return "insufficient_data"
    pct = (newest - oldest) / oldest * 100
    recent_spread = (max(volumes[:3]) - min(volumes[:3])) / oldest * 100 if len(volumes) >= 3 else abs(pct)
    if pct >= 5:
        return "improving"
    elif pct <= -5:
        return "declining"
    elif recent_spread < 3:
        return "stagnant"
    else:
        return "mixed"


def build_exercise_from_history_api(session: requests.Session, exercise_name: str) -> dict:
    """GET /exercises/:title/history — server returns sessions newest first."""
    data = fetch_exercise_history(session, exercise_name, limit=HISTORY_PER_EXERCISE)
    history = []
    for sess in data.get("sessions", []):
        sets = sess.get("sets") or []
        history.append({
            "date": fmt_date_iso(sess.get("date")),
            "sets": sets_summary_lbs(sets),
            "volume_lbs": volume_lbs_from_sets(sets),
        })

    volumes = [h["volume_lbs"] for h in history]
    overall_change_pct = None
    if len(volumes) >= 2 and volumes[-1]:
        overall_change_pct = round((volumes[0] - volumes[-1]) / volumes[-1] * 100, 1)

    return {
        "name": data.get("exercise", exercise_name),
        "sessions": history,
        "trend": trend_label(volumes),
        "overall_volume_change_pct": overall_change_pct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-exercise trend data for a workout")
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        metavar="N",
        help="Analyze the Nth most recent workout (0 = latest; uses /workouts/latest when 0)",
    )
    args = parser.parse_args()

    session = get_session()
    latest = fetch_workout_at_index(session, args.index)

    if latest is None:
        print(json.dumps({"error": "No workouts found."}))
        sys.exit(0)

    exercise_names = [e["title"] for e in latest.get("exercises", [])]

    if not exercise_names:
        print(json.dumps({"error": "Workout has no exercises recorded."}))
        sys.exit(0)

    exercises = [build_exercise_from_history_api(session, name) for name in exercise_names]

    print(
        json.dumps(
            {
                "latest_title": latest["title"],
                "latest_date": fmt_date_workout(latest),
                "unit": "lbs",
                "exercises": exercises,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
