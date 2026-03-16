#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' package is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

ENV_API_KEY = "YELP_API_KEY"
YELP_API_URL = "https://api.yelp.com/v3/businesses/search"
MIN_RATING = 4.5
DEFAULT_LIMIT = 10
MAX_LIMIT = 15

_SKILL_DIR = Path(__file__).resolve().parent.parent

def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        env_file = _SKILL_DIR / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass


def get_api_key() -> str:
    _load_dotenv()
    key = os.environ.get(ENV_API_KEY)
    if not key:
        print(
            f"Error: YELP_API_KEY is not set. Add it to your environment or {_SKILL_DIR / '.env'}",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def search_restaurants(location: str, category: str, limit: int, sort_by: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    params = {
        "location": location,
        "categories": category,
        "limit": MAX_LIMIT,
        "sort_by": sort_by,
    }

    try:
        resp = requests.get(YELP_API_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        body = exc.response.json() if exc.response is not None else {}
        msg = body.get("error", {}).get("description", str(exc))
        print(f"Yelp API error: {msg}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(1)

    businesses = resp.json().get("businesses", [])
    filtered = [b for b in businesses if b.get("rating", 0) >= MIN_RATING and not b.get("is_closed")]
    return filtered[:limit]


def format_table(restaurants: list[dict]) -> str:
    if not restaurants:
        return f"No restaurants with a {MIN_RATING}+ rating were found for that location."

    rows = []
    header = f"{'#':<4} {'Name':<35} {'Rating':<8} {'Reviews':<9} {'Price':<7} {'Address'}"
    rows.append(header)
    rows.append("-" * len(header))

    for i, biz in enumerate(restaurants, 1):
        name = biz.get("name", "N/A")[:34]
        rating = biz.get("rating", "N/A")
        review_count = biz.get("review_count", 0)
        price = biz.get("price", "N/A")
        location_data = biz.get("location", {})
        address = location_data.get("display_address", [])
        address_str = ", ".join(address)
        rows.append(f"{i:<4} {name:<35} {rating:<8} {review_count:<9} {price:<7} {address_str}")

    return "\n".join(rows)


def format_json(restaurants: list[dict]) -> str:
    output = []
    for biz in restaurants:
        location_data = biz.get("location", {})
        output.append({
            "name": biz.get("name"),
            "rating": biz.get("rating"),
            "review_count": biz.get("review_count"),
            "price": biz.get("price"),
            "phone": biz.get("display_phone"),
            "address": ", ".join(location_data.get("display_address", [])),
            "zipcode": location_data.get("zip_code"),
            "url": biz.get("url"),
            "categories": [c.get("title") for c in biz.get("categories", [])],
        })
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description=f"Find restaurants with a {MIN_RATING}+ Yelp rating by location."
    )
    parser.add_argument("location", help="Zipcode, city, or address (e.g. '10001' or 'Brooklyn, NY')")
    parser.add_argument(
        "--category",
        default="restaurants",
        help="Yelp category alias (default: restaurants). Examples: pizza, sushi, italian",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max results to return (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )
    parser.add_argument(
        "--sort-by",
        choices=["best_match", "rating", "review_count", "distance"],
        default="rating",
        help="Sort order (default: rating)",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    limit = max(1, min(args.limit, MAX_LIMIT))
    restaurants = search_restaurants(args.location, args.category, limit, args.sort_by)

    if args.output == "json":
        print(format_json(restaurants))
    else:
        print(f"\nTop-rated restaurants (≥{MIN_RATING}★) near {args.location}\n")
        print(format_table(restaurants))
        print(f"\n{len(restaurants)} result(s) found.")


if __name__ == "__main__":
    main()
