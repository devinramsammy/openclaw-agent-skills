#!/usr/bin/env python3
"""
Look up NYC restaurant health inspection grades by borough and name.
Caches borough data locally with a 7-day TTL.

Usage:
  python restaurant_health.py search <borough> "<name>" [--refresh]
  python restaurant_health.py list-boroughs
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

API_URL = "https://a816-health.nyc.gov/ABCEatsRestaurants/App/GetEntitiesByBoro/{borough}"

# Public API; 15s is generous for a list response
REQUEST_TIMEOUT = 15

CACHE_TTL_DAYS = 7

SEARCH_FIELDS = {
    "name": "EntityName",
    "address": "MostRecentVendingLocation",
    "zipcode": "MostRecentZipCode",
    "cuisine": "Cuisine",
}

VALID_BOROUGHS = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "statenisland": "Staten Island",
    "staten island": "Staten Island",
}

CACHE_DIR = Path(__file__).parent.parent / "cache"


def resolve_borough(raw: str) -> str:
    key = raw.lower().strip()
    if key in VALID_BOROUGHS:
        return VALID_BOROUGHS[key]
    print(
        f"ERROR: Unknown borough '{raw}'. "
        f"Valid boroughs: {', '.join(sorted(set(VALID_BOROUGHS.values())))}",
        file=sys.stderr,
    )
    sys.exit(1)


def cache_path(borough: str) -> Path:
    return CACHE_DIR / f"{borough.lower().replace(' ', '_')}.json"


def is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with open(path) as f:
            data = json.load(f)
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        return datetime.now(timezone.utc) - fetched_at < timedelta(days=CACHE_TTL_DAYS)
    except (json.JSONDecodeError, KeyError, ValueError):
        return False


def fetch_borough(borough: str) -> list:
    url = API_URL.format(borough=urllib.parse.quote(borough))
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not fetch data for {borough}: {exc}", file=sys.stderr)
        print("Check your internet connection and retry.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON response for {borough}", file=sys.stderr)
        sys.exit(1)


def load_restaurants(borough: str, force_refresh: bool = False) -> list:
    path = cache_path(borough)

    if not force_refresh and is_cache_fresh(path):
        with open(path) as f:
            return json.load(f)["restaurants"]

    restaurants = fetch_borough(borough)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "restaurants": restaurants,
        }, f)
    print(f"Cached {len(restaurants)} restaurants for {borough}", file=sys.stderr)
    return restaurants


def search(restaurants: list, query: str, field: str = "name") -> list:
    q = query.lower()
    api_field = SEARCH_FIELDS.get(field, "EntityName")
    matches = []
    for r in restaurants:
        if q in str(r.get(api_field, "")).lower():
            matches.append({
                "EntityName": r.get("EntityName", ""),
                "Grade": r.get("Grade", "N/A"),
                "Cuisine": r.get("Cuisine", ""),
                "Address": r.get("MostRecentVendingLocation", ""),
                "ZipCode": r.get("MostRecentZipCode", ""),
            })
    return matches


def parse_borough_and_name(args: list) -> tuple:
    """Try two-word borough first (e.g. 'staten island'), then single word."""
    if len(args) >= 3:
        two_word = f"{args[0]} {args[1]}".lower().strip()
        if two_word in VALID_BOROUGHS:
            return VALID_BOROUGHS[two_word], " ".join(args[2:])
    if args:
        one_word = args[0].lower().strip()
        if one_word in VALID_BOROUGHS:
            return VALID_BOROUGHS[one_word], " ".join(args[1:])
    return None, None


def cmd_search(args: list) -> None:
    force_refresh = "--refresh" in args
    args = [a for a in args if a != "--refresh"]

    field = "name"
    if "--by" in args:
        idx = args.index("--by")
        if idx + 1 >= len(args):
            print("ERROR: --by requires a field argument (name, address, zipcode, cuisine)", file=sys.stderr)
            sys.exit(1)
        field = args[idx + 1].lower()
        args = args[:idx] + args[idx + 2:]
        if field not in SEARCH_FIELDS:
            print(
                f"ERROR: Unknown field '{field}'. Valid fields: {', '.join(SEARCH_FIELDS)}",
                file=sys.stderr,
            )
            sys.exit(1)

    borough, query = parse_borough_and_name(args)
    if not borough or not query:
        print(
            "Usage: restaurant_health.py search <borough> \"<query>\" [--by name|address|zipcode|cuisine] [--refresh]",
            file=sys.stderr,
        )
        sys.exit(1)

    restaurants = load_restaurants(borough, force_refresh=force_refresh)
    results = search(restaurants, query, field=field)

    if not results:
        print(f"No restaurants matching '{query}' by {field} found in {borough}.")
        return

    print(json.dumps(results, indent=2))


def cmd_list_boroughs() -> None:
    for b in sorted(set(VALID_BOROUGHS.values())):
        print(b)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: restaurant_health.py <search|list-boroughs> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        cmd_search(sys.argv[2:])
    elif cmd == "list-boroughs":
        cmd_list_boroughs()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
