---
name: checking-restaurant-health
description: Look up NYC restaurant health inspection grades by name, zipcode, cusine, or borough. Use when the user asks about a restaurant's health grade, inspection rating, cleanliness score, or food safety in NYC.
---

# NYC Restaurant Health Ratings

Look up health inspection grades for NYC restaurants.

## Run

```bash
python skills/restaurant-health/scripts/restaurant_health.py search <borough> "<restaurant name>"
```

Boroughs: `Manhattan`, `Brooklyn`, `Queens`, `Bronx`, `Staten Island`

To list valid boroughs:

```bash
python skills/restaurant-health/scripts/restaurant_health.py list-boroughs
```

Search by address, zipcode, or cuisine using `--by`:

```bash
python skills/restaurant-health/scripts/restaurant_health.py search <borough> "<query>" --by <field>
```

Valid fields: `name` (default), `address`, `zipcode`, `cuisine`

Force a fresh API fetch (ignores cache):

```bash
python skills/restaurant-health/scripts/restaurant_health.py search --refresh <borough> "<name>"
```

## Output

When reporting results, respond with **only** a table per matching restaurant. No extra explanation or commentary. No extra notes.

| Field   | Value        |
| ------- | ------------ |
| Name    | JOE'S PIZZA  |
| Grade   | A            |
| Cuisine | Pizza        |
| Address | 7 CARMINE ST |
| ZipCode | 10014        |

If multiple locations match, show one table per result. If no matches are found, say so briefly.

## Caching

Borough data is cached at `skills/restaurant-health/cache/{borough}.json` with a 7-day TTL. The script auto-refreshes stale caches. Use `--refresh` to force.

## Constraints

- Data comes from the NYC Department of Health; may lag behind real-time inspections
- Search is case-insensitive substring match on restaurant name
