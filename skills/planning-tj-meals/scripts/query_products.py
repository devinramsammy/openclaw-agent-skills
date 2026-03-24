#!/usr/bin/env python3
"""Filter Trader Joe's products from food_products.jsonl by keyword and protein content."""

import argparse
import json
import re
import sys
from pathlib import Path

MEAL_TYPE_KEYWORDS = {
    "breakfast": [
        "breakfast", "morning", "egg", "eggs", "oatmeal", "cereal", "granola",
        "pancake", "waffle", "yogurt", "bagel", "muffin", "sausage", "bacon",
        "hash", "toast", "smoothie", "overnight",
    ],
    "lunch": [
        "lunch", "sandwich", "wrap", "salad", "soup", "bowl", "burrito",
        "quesadilla", "pita", "hummus", "deli", "tuna",
    ],
    "dinner": [
        "dinner", "entrée", "entree", "steak", "chicken", "salmon", "shrimp",
        "pasta", "curry", "stir fry", "stir-fry", "roast", "grill", "bake",
        "casserole", "meatball", "bulgogi", "tikka", "lasagna", "pizza",
        "seafood", "fish", "pork", "beef", "lamb", "tofu", "tempeh",
    ],
    "snack": [
        "snack", "bar", "nuts", "trail mix", "chips", "crackers", "jerky",
        "popcorn", "dip", "hummus", "cheese", "dried fruit",
    ],
    "produce": [
        "spinach", "kale", "arugula", "lettuce", "greens", "broccoli", "carrot",
        "tomato", "pepper", "mushroom", "avocado", "zucchini", "squash",
        "asparagus", "green bean", "pea", "corn", "beet", "cabbage", "bok choy",
        "edamame", "apple", "banana", "mango", "berry", "orange", "lemon",
        "lime", "grape", "peach", "citrus", "pineapple", "melon", "herb",
        "basil", "cilantro", "ginger", "salad kit", "salad blend", "salad mix",
        "vegetable", "veggie", "fruit",
    ],
}

# Produce items have naturally low protein — bypass the protein floor for this meal type
PRODUCE_MIN_PROTEIN_DEFAULT = 0

HTML_TAG_RE = re.compile(r"<[^>]+>")
PROTEIN_RE = re.compile(r"(\d+)\s*g", re.IGNORECASE)


def strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text).strip()


def first_sentence(text: str) -> str:
    text = strip_html(text)
    for end in (".", "!", "?"):
        idx = text.find(end)
        if idx != -1:
            return text[: idx + 1]
    return text[:200]


def parse_protein(nutrition_list: list) -> int:
    if not nutrition_list:
        return 0
    panel = nutrition_list[0]
    for detail in panel.get("details", []):
        if detail.get("nutritional_item") == "Protein":
            m = PROTEIN_RE.search(detail.get("amount", ""))
            return int(m.group(1)) if m else 0
    return 0


def parse_calories(nutrition_list: list) -> str:
    if not nutrition_list:
        return ""
    return nutrition_list[0].get("calories_per_serving", "").strip()


def parse_serving_size(nutrition_list: list) -> str:
    if not nutrition_list:
        return ""
    return nutrition_list[0].get("serving_size", "").strip()


def matches_keywords(title: str, marketing: str, keywords: list[str]) -> bool:
    combined = f"{title} {marketing}".lower()
    return any(kw in combined for kw in keywords)


def build_product_record(product: dict, protein_g: int) -> dict:
    nutrition = product.get("nutrition", [])
    marketing = product.get("item_story_marketing", "")
    return {
        "title": product.get("item_title", ""),
        "price": product.get("price", {}).get("value"),
        "calories_per_serving": parse_calories(nutrition),
        "protein_g": protein_g,
        "serving_size": parse_serving_size(nutrition),
        "prep_hint": first_sentence(marketing),
    }


def find_jsonl_path() -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    candidates = [
        skill_root / "references" / "food_products.jsonl",
        skill_root / "food_products.jsonl",
        Path("food_products.jsonl"),
    ]
    for c in candidates:
        if c.exists():
            return c
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir
    for _ in range(8):
        repo_root = repo_root.parent
        for rel in ("references/food_products.jsonl", "food_products.jsonl"):
            candidate = repo_root / rel
            if candidate.exists():
                return candidate
    print("Error: food_products.jsonl not found", file=sys.stderr)
    sys.exit(1)


FROZEN_SIGNALS = {"frozen", "freezer"}


def is_frozen(title: str, marketing: str) -> bool:
    combined = f"{title} {marketing}".lower()
    return any(sig in combined for sig in FROZEN_SIGNALS)


def main():
    parser = argparse.ArgumentParser(description="Query TJ products for meal planning")
    parser.add_argument("--meal-type", choices=list(MEAL_TYPE_KEYWORDS.keys()))
    parser.add_argument("--keywords", nargs="+", default=[])
    parser.add_argument("--min-protein", type=int, default=None,
                        help="Min grams protein per serving (default: 0 for produce, 12 for others)")
    parser.add_argument("--max-price", type=float, default=None)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--data-file", type=str, default=None)
    parser.add_argument("--exclude-frozen", action="store_true",
                        help="Exclude products that mention frozen/freezer in title or marketing")
    parser.add_argument("--exclude-keywords", nargs="+", default=[],
                        help="Exclude products whose title or marketing contains any of these terms")
    parser.add_argument("--title-only", action="store_true",
                        help="Match keywords against item title only, not marketing text (useful for produce)")
    parser.add_argument("--include-no-nutrition", action="store_true",
                        help="Include items that have no nutrition data (e.g. fresh produce). "
                             "Protein and calorie fields will be null.")
    args = parser.parse_args()

    is_produce = args.meal_type == "produce"
    title_only = args.title_only or is_produce
    include_no_nutrition = args.include_no_nutrition or is_produce
    if args.min_protein is not None:
        min_protein = args.min_protein
    else:
        min_protein = PRODUCE_MIN_PROTEIN_DEFAULT if is_produce else 12

    search_keywords = [kw.lower() for kw in args.keywords]
    if args.meal_type:
        search_keywords.extend(MEAL_TYPE_KEYWORDS[args.meal_type])

    data_path = Path(args.data_file) if args.data_file else find_jsonl_path()
    if not data_path.exists():
        print(f"Error: {data_path} not found", file=sys.stderr)
        sys.exit(1)

    results = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)
            except json.JSONDecodeError:
                continue

            nutrition = product.get("nutrition")
            if not nutrition:
                if not include_no_nutrition:
                    continue
                protein_g = None
            else:
                protein_g = parse_protein(nutrition)
                if protein_g < min_protein:
                    continue

            title = product.get("item_title", "")
            marketing = strip_html(product.get("item_story_marketing", "") or "")

            if args.exclude_frozen and is_frozen(title, marketing):
                continue

            if args.exclude_keywords:
                combined = f"{title} {marketing}".lower()
                if any(kw.lower() in combined for kw in args.exclude_keywords):
                    continue

            match_text = title if title_only else f"{title} {marketing}"
            if search_keywords and not matches_keywords(match_text, "", search_keywords):
                continue

            price = product.get("price", {}).get("value")
            if args.max_price is not None and price is not None and price > args.max_price:
                continue

            results.append(build_product_record(product, protein_g))
            if len(results) >= args.limit:
                break

    results.sort(key=lambda r: (r["protein_g"] is not None, r["protein_g"] or 0), reverse=True)
    json.dump(results, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
