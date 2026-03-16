---
name: restaurant-ratings
description: Finds highly-rated restaurants (4.5+ stars) using the Yelp Fusion API by zipcode, city, or address. Optionally filter by cuisine (pizza, sushi, italian, etc.). Use when the user asks to find top restaurants, best places to eat, highly-rated restaurants, or good food near a location or zipcode.
---

# Restaurant Ratings

Find restaurants with a 4.5+ Yelp rating near any location using the Yelp Fusion API.

## Setup

**If `.venv` does not exist** — create, activate, and install:

```bash
cd $HOME/.openclaw/skills/restaurant-ratings
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**If `.venv` already exists** — activate only:

```bash
cd $HOME/.openclaw/skills/restaurant-ratings
source .venv/bin/activate
```

## Run

```bash
$HOME/.openclaw/skills/restaurant-ratings/.venv/bin/python3 \
  $HOME/.openclaw/skills/restaurant-ratings/scripts/find_restaurants.py \
  "<location>"
```

`<location>` can be a zipcode (`10001`), city (`Brooklyn, NY`), or address.

### Optional flags

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--category` | Yelp alias | `restaurants` | Cuisine alias to pass to the API. Look up the correct alias in [categories.md](categories.md) before running (e.g. "indian" → `indpak`). |
| `--limit` | 1–50 | 10 | Max results |
| `--sort-by` | `rating`, `best_match`, `review_count`, `distance` | `rating` | Sort order |
| `--output` | `table`, `json` | `table` | Output format |

### Examples

```bash
$HOME/.openclaw/skills/restaurant-ratings/.venv/bin/python3 \
  $HOME/.openclaw/skills/restaurant-ratings/scripts/find_restaurants.py "10001"

$HOME/.openclaw/skills/restaurant-ratings/.venv/bin/python3 \
  $HOME/.openclaw/skills/restaurant-ratings/scripts/find_restaurants.py "Brooklyn, NY" \
  --category sushi --limit 5

$HOME/.openclaw/skills/restaurant-ratings/.venv/bin/python3 \
  $HOME/.openclaw/skills/restaurant-ratings/scripts/find_restaurants.py "94105" \
  --output json
```

## Output

Present results as a formatted list or table. Example:

```
Top-rated restaurants (≥4.5★) near 10001

#    Name                                Rating   Reviews   Price   Address
---  ----------------------------------  -------  --------  ------  ----------------------------
1    Joe's Pizza                         4.8      1234      $       7 Carmine St, New York, NY
2    Westville Hudson                    4.6      876       $$      333 Hudson St, New York, NY
```

If no results are found, say so briefly and suggest broadening the search (different location or no category filter).

## Constraints

- Results are filtered to businesses with rating ≥ 4.5 and that are not permanently closed
- Yelp API returns up to 50 results per call; the script applies the rating filter locally
