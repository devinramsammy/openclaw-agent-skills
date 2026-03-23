#!/usr/bin/env python3
"""Fetch Catch Corner tennis facility rental availability (quick-view API)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import requests

NY_TZ = ZoneInfo("America/New_York")
UTC = timezone.utc

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

ARENA_NAMES: dict[int, str] = {
    1253: "Cunningham Tennis",
    922: "Alley Pond Tennis",
    1039: "McCarren Tennis",
}

ARENA_ALIASES: dict[str, int] = {
    "1253": 1253,
    "922": 922,
    "1039": 1039,
    "cunningham": 1253,
    "alley-pond": 922,
    "alleypond": 922,
    "mccarren": 1039,
    "mccarren-tennis": 1039,
}

# All configured arenas (order: Cunningham, Alley Pond, McCarren).
ALL_ARENA_IDS: list[int] = [1253, 922, 1039]

# Short labels for stdout (no "Tennis", no timezone suffixes).
SHORT_ARENA_NAMES: dict[int, str] = {
    1253: "Cunningham",
    922: "Alley Pond",
    1039: "McCarren",
}

QUICK_VIEW_PATH_ID = 20

POST_BODY_TEMPLATE: dict[str, Any] = {
    "neighbourhoodList": [],
    "arenaList": [],
    "quickViewDateFilters": [],
    "arenaId": -1,
    "listingType": "facility-rentals",
    "sportType": "Tennis",
    "explicitFilter": None,
    "dateInterval": None,
    "calendarReferences": None,
    "quickViewDateFiltersStore": [],
}


def _parse_iso_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_z_param(dt: datetime) -> str:
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def utc_sunday_week_start(dt: datetime) -> datetime:
    """UTC midnight Sunday of the week containing dt (Monday=0 .. Sunday=6)."""
    dt = dt.astimezone(UTC)
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (dt.weekday() + 1) % 7
    return midnight - timedelta(days=days_since_sunday)


def iter_week_starts_utc(range_from: datetime, range_to: datetime) -> Iterator[datetime]:
    """Yield UTC Sunday midnights for each week overlapping [range_from, range_to)."""
    rf = range_from.astimezone(UTC)
    rt = range_to.astimezone(UTC)
    if rt <= rf:
        return
    ws = utc_sunday_week_start(rf)
    while ws < rt:
        if ws + timedelta(days=7) > rf:
            yield ws
        ws += timedelta(days=7)


def parse_slot_datetime(raw: str) -> datetime:
    """API returns naive strings; treat as America/New_York."""
    dt = datetime.fromisoformat(raw.strip())
    if dt.tzinfo is not None:
        return dt.astimezone(NY_TZ)
    return dt.replace(tzinfo=NY_TZ)


def _compact_clock(dt: datetime) -> str:
    """12-hour wall time in America/New_York; hour only if :00, else h:mm; always AM/PM."""
    dt = dt.astimezone(NY_TZ)
    h12 = dt.hour % 12
    if h12 == 0:
        h12 = 12
    m = dt.minute
    ap = dt.strftime("%p")
    if m == 0:
        return f"{h12} {ap}"
    return f"{h12}:{m:02d} {ap}"


def _compact_range(start: datetime, end: datetime) -> str:
    return f"{_compact_clock(start)} – {_compact_clock(end)}"


def slot_overlaps_filter(
    start_raw: str,
    end_raw: str,
    filter_from: datetime,
    filter_to: datetime,
) -> bool:
    s = parse_slot_datetime(start_raw).astimezone(UTC)
    e = parse_slot_datetime(end_raw).astimezone(UTC)
    ff = filter_from.astimezone(UTC)
    ft = filter_to.astimezone(UTC)
    return s < ft and e > ff


def resolve_arenas(arg: str) -> list[int]:
    a = arg.strip().lower()
    if a in ("both", "all"):
        return list(ALL_ARENA_IDS)
    if a not in ARENA_ALIASES:
        raise SystemExit(
            "Unknown arena {0!r}. Use 1253, 922, 1039, cunningham, alley-pond, "
            "mccarren, or both/all.".format(arg)
        )
    return [ARENA_ALIASES[a]]


def fetch_week(
    session: requests.Session,
    arena_id: int,
    week_start: datetime,
) -> list[dict[str, str]]:
    week_end = week_start + timedelta(days=7)
    url = (
        f"https://www.catchcorner.com/api/client/listings/filter/rental/"
        f"quick-view/{QUICK_VIEW_PATH_ID}"
    )
    params = {"start": _to_z_param(week_start), "end": _to_z_param(week_end)}
    body = dict(POST_BODY_TEMPLATE)
    body["arenaList"] = [arena_id]

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    r = session.post(url, params=params, headers=headers, json=body, timeout=60)
    if not r.ok:
        print(f"HTTP {r.status_code}: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)

    try:
        data = r.json()
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}\nBody: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(f"Expected JSON array, got {type(data).__name__}", file=sys.stderr)
        sys.exit(1)

    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        sd = item.get("startDate")
        ed = item.get("endDate")
        if isinstance(sd, str) and isinstance(ed, str):
            out.append({"startDate": sd, "endDate": ed})
    return out


def format_grouped_by_day(rows: list[dict[str, Any]]) -> str:
    """Group by local day, then by arena: one line per arena, comma-separated compact ranges."""
    by_day: dict[date, dict[int, list[tuple[datetime, datetime]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        aid = row["arenaId"]
        try:
            s = parse_slot_datetime(row["startDate"])
            e = parse_slot_datetime(row["endDate"])
        except ValueError:
            continue
        day_key = s.astimezone(NY_TZ).date()
        by_day[day_key][aid].append((s, e))

    if not by_day:
        return "(no slots)"

    out: list[str] = []
    for d in sorted(by_day.keys()):
        label = datetime(d.year, d.month, d.day, tzinfo=NY_TZ).strftime("%a %b ") + str(d.day)
        out.append(label)
        arenas_here = sorted(
            by_day[d].keys(),
            key=lambda i: SHORT_ARENA_NAMES.get(i, f"id{i}"),
        )
        for aid in arenas_here:
            label_name = SHORT_ARENA_NAMES.get(aid, f"Arena {aid}")
            slots = sorted(by_day[d][aid], key=lambda t: t[0])
            parts = [_compact_range(s, e) for s, e in slots]
            out.append(f"{label_name}: {', '.join(parts)}")
        out.append("")
    return "\n".join(out).rstrip()


def main() -> None:
    p = argparse.ArgumentParser(description="Catch Corner tennis quick-view availability")
    p.add_argument(
        "--arena",
        required=True,
        help="1253, 922, 1039, cunningham, alley-pond, mccarren, or both/all",
    )
    p.add_argument("--week-start", metavar="YYYY-MM-DD", help="Single week containing this date (UTC week)")
    p.add_argument("--from", dest="from_ts", metavar="ISO8601", help="Range start (UTC)")
    p.add_argument("--to", dest="to_ts", metavar="ISO8601", help="Range end (UTC)")
    p.add_argument("--filter-from", dest="filter_from", metavar="ISO8601", help="Filter window start")
    p.add_argument("--filter-to", dest="filter_to", metavar="ISO8601", help="Filter window end")
    args = p.parse_args()

    if (args.from_ts is None) ^ (args.to_ts is None):
        print("Use --from and --to together, or neither.", file=sys.stderr)
        sys.exit(2)

    if (args.filter_from is None) ^ (args.filter_to is None):
        print("Use --filter-from and --filter-to together, or neither.", file=sys.stderr)
        sys.exit(2)

    if args.week_start and (args.from_ts or args.to_ts):
        print("Use either --week-start or --from/--to, not both.", file=sys.stderr)
        sys.exit(2)

    now = datetime.now(UTC)

    if args.week_start:
        d = date.fromisoformat(args.week_start.strip())
        week_anchor = datetime(d.year, d.month, d.day, tzinfo=UTC)
        range_from = utc_sunday_week_start(week_anchor)
        range_to = range_from + timedelta(days=7)
    elif args.from_ts and args.to_ts:
        range_from = _parse_iso_utc(args.from_ts)
        range_to = _parse_iso_utc(args.to_ts)
    else:
        range_from = utc_sunday_week_start(now)
        range_to = range_from + timedelta(days=7)

    if range_to <= range_from:
        print("--to must be after --from", file=sys.stderr)
        sys.exit(2)

    filter_from = _parse_iso_utc(args.filter_from) if args.filter_from else None
    filter_to = _parse_iso_utc(args.filter_to) if args.filter_to else None
    if filter_from is not None and filter_to is not None and filter_to <= filter_from:
        print("--filter-to must be after --filter-from", file=sys.stderr)
        sys.exit(2)

    arena_ids = resolve_arenas(args.arena)
    week_starts = list(iter_week_starts_utc(range_from, range_to))
    if not week_starts:
        print("No weeks in range.", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    results: list[dict[str, Any]] = []

    for arena_id in arena_ids:
        name = ARENA_NAMES.get(arena_id, f"Arena {arena_id}")
        for ws in week_starts:
            slots = fetch_week(session, arena_id, ws)
            for slot in slots:
                results.append(
                    {
                        "arenaId": arena_id,
                        "arenaName": name,
                        "startDate": slot["startDate"],
                        "endDate": slot["endDate"],
                    }
                )

    if filter_from is not None and filter_to is not None:
        results = [
            r
            for r in results
            if slot_overlaps_filter(
                r["startDate"], r["endDate"], filter_from, filter_to
            )
        ]

    def _row_sort_key(r: dict[str, Any]) -> tuple:
        try:
            return (parse_slot_datetime(r["startDate"]), str(r["arenaName"]))
        except ValueError:
            return (datetime.min.replace(tzinfo=UTC), "")

    results.sort(key=_row_sort_key)

    print(format_grouped_by_day(results))


if __name__ == "__main__":
    main()
