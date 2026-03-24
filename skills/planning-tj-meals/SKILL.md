---
name: planning-tj-meals
description: Generates Trader Joe's meal plans and grocery lists from the repo product database via query_products.py. Use when the user asks for a meal plan, grocery list, weekly meals, meal ideas, or Trader Joe's meal suggestions; supports day counts and meal types (breakfast, lunch, dinner).
---

# Trader Joe's Meal Planner & Grocery List

## Setup

`scripts/query_products.py` uses only the Python standard library (no `pip` dependencies). Invoke it with `python3` and full paths so the agent never needs to `cd` first:

```bash
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --help
```

The script reads `references/food_products.jsonl` relative to the skill root (resolved from the script path).

## Workflow / Commands

Copy and track progress:

```
Meal plan progress:
- [ ] Preferences gathered (days, meals, goals, restrictions, budget, frozen ok)
- [ ] query_products.py run for each meal type + produce (default --exclude-frozen)
- [ ] Plan composed: dish-first, macros met, produce included, ingredients shared
- [ ] Output: grocery list first, then overview table, then day-by-day
```

### Step 1: Gather preferences

Ask or infer from context:

- **Days**: How many days? (default: 7)
- **Meals**: Which meals to plan — `breakfast`, `lunch`, `dinner`, or any combination (default: all three)
- **Goals**: weight loss, muscle gain, maintenance, or balanced (affects calorie and macro emphasis)
- **Dietary restrictions**: vegetarian, gluten-free, dairy-free, etc.
- **Budget**: max price per item or total weekly budget
- **Frozen ok?**: Default is fresh/refrigerated only; ask only if relevant

### Step 2: Query products

Run the script for each requested meal category. Always include `--exclude-frozen` by default. Use `--min-protein 10` to get enough candidates across all macro roles (protein, carb, fat sources).

```bash
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --meal-type breakfast --min-protein 10 --limit 40 --exclude-frozen
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --meal-type lunch --min-protein 10 --limit 40 --exclude-frozen
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --meal-type dinner --min-protein 10 --limit 60 --exclude-frozen
```

### Step 2b: Query fresh produce

**Always run this query** to get the fresh vegetable and fruit options available. Fresh produce items don't have nutrition data in the TJ's database, so their protein/calorie fields will be `null` — use well-known nutrition estimates for those items when composing the plan.

```bash
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --meal-type produce --exclude-frozen --limit 50 --exclude-keywords candy popcorn chips muffin cookie "ice cream" bar pretzel cracker cereal granola
```

This query automatically uses title-only matching and bypasses the protein minimum, so only items with produce-related titles are returned. Pick 1–2 produce items per meal to fill the **fresh veg / fresh fruit** role.

For user-specified ingredients or cuisine, add `--keywords`:

```bash
python3 $HOME/.openclaw/skills/planning-tj-meals/scripts/query_products.py --keywords salmon chicken --min-protein 10 --limit 40 --exclude-frozen
```

For budget constraints, add `--max-price N`. To include frozen products, omit `--exclude-frozen`.

### Step 3: Compose the plan

**Start with a dish concept, then fill it with products.** Do not start with products and figure out what to do with them.

Good dinner formats to pull from:

- **Tacos / burritos** — a seasoned protein (birria, shawarma chicken, pulled pork) in tortillas with toppings
- **Pasta dish** — meatballs in marinara, sausage with chickpea fusilli, salmon over lentil pasta with lemon-herb sauce
- **Sheet pan dinner** — chicken thighs or salmon fillet roasted alongside vegetables, served with a grain or bread
- **Rice / grain bowl** — pulled chicken or steak tips over rice with a sauce (teriyaki, salsa verde, tzatziki)
- **Burger / sandwich plate** — beef or turkey patties on a bun with a side salad or roasted vegetable
- **Stir-fry** — shaved lamb or sliced chicken with vegetables over noodles or rice
- **BBQ plate** — pulled pork or smoked chicken with coleslaw, beans, and cornbread
- **Soup / stew meal** — chili, birria, or broccoli cheddar soup served with crusty bread or a grain
- **Curry or stew over rice** — lamb, chicken, or lentil-based with a TJ curry sauce

For each dish, select 2–5 products that fill the natural roles of that dish and together satisfy the macro targets:

- **Protein** — the main (meat, fish, tofu)
- **Carb vehicle** — what you eat it on or with (pasta, tortillas, rice, bread, lentil base)
- **Sauce / fat layer** — what makes it taste like a real meal (yogurt sauce, cheese, olive oil, teriyaki glaze)
- **Fiber/veg element** — something that adds bulk, texture, and fiber (legume pasta, beans, vegetable-forward product)
- **Fresh produce** — a real vegetable or fruit from the produce query results, playing a natural role in the dish (e.g., arugula in a salad, bell peppers in a stir-fry, avocado on a burger, spinach wilted into pasta, sliced tomatoes alongside protein, banana or apple as a breakfast side). **Every meal should include at least one fresh produce item.** Use standard nutrition estimates for items with null data (e.g., avocado ~240 cal / 3g P / 13g C / 22g F, banana ~105 cal / 1g P / 27g C / 0g F, bell pepper ~30 cal / 1g P / 7g C / 0g F, arugula/spinach/kale ~10–20 cal / 2g P / 2g C / 0g F per cup, cherry tomatoes ~30 cal / 1g P / 6g C / 0g F per cup, mushrooms ~20 cal / 3g P / 3g C / 0g F per cup).

Check that the combined nutritional values land within the target ranges. If a macro is short, adjust portion size or add a complementary product. Avoid exceeding sodium or calorie caps by more than 10%.

Vary cuisine styles across days (e.g., Mexican → Italian → Middle Eastern → American → Mediterranean). Never repeat the same dish format two days in a row.

**Actively design for ingredient sharing.** Before finalizing the plan, look at every product and ask: can this appear in a second meal in a different role? A pack of smoked salmon used for lox toast at breakfast can come back as a salmon rice bowl at lunch. Pulled chicken in tacos at dinner can be the protein in a grain bowl for tomorrow's lunch. Chickpea fusilli used in a pasta dish can be tossed cold with tuna and olive oil for a pasta salad. Aim for at least 2–3 products that do double duty. Combine their quantities into a single grocery list line.

Note raw quantities needed per product across all days for the grocery list.

### Step 4: Output

Use this template exactly. The **Grocery List comes first** — it is the primary output.

```
## Grocery List

| Product | Qty | Unit Price | Subtotal | Fresh/Refrigerated |
|---------|-----|------------|----------|--------------------|
| ...     | 2   | $X.XX      | $X.XX    | ✓                  |
| ...     | 1   | $X.XX      | $X.XX    |                    |

**Estimated total: $XX.XX**

---

## Meal Plan — [N]-Day Overview

| Day | [Breakfast] | [Lunch] | [Dinner] |
|-----|-------------|---------|----------|
| 1   | Dish name (~Xcal, Xg P / Xg C / Xg F) | ... | ... |
| 2   | ...         | ...     | ...      |

*(Only include columns for the meal types the user requested.)*

---

## Day-by-Day

### Day 1
**[Dish name]** — [one-line description of the dish as you'd describe it to someone, e.g. "Beef birria tacos with warm corn tortillas and a side of salsa verde"]
*~X cal | Xg protein / Xg carbs / Xg fat | Xg fiber*

- **[Culinary role]** — Product A (Xg P — $X.XX): how it's used in the dish
- **[Culinary role]** — Product B (Xg P — $X.XX): how it's used in the dish

### Day 2
...
```

### Reference

Calibrated breakfast, lunch, and dinner compositions → [EXAMPLES.md](references/EXAMPLES.md). Read when calibrating portion and macro balance; skip if the task is already clear.

### Script reference

`scripts/query_products.py` — stdlib-only, reads `references/food_products.jsonl` under this skill directory.

| Flag                     | Description                                                              | Default                          |
| ------------------------ | ------------------------------------------------------------------------ | -------------------------------- |
| `--meal-type`            | `breakfast`, `lunch`, `dinner`, `snack`, or `produce`                    | none                             |
| `--keywords`             | Space-separated search terms                                             | none                             |
| `--min-protein`          | Min grams protein per serving                                            | `0` for produce, `12` for others |
| `--max-price`            | Max price per item                                                       | none                             |
| `--limit`                | Max results returned                                                     | `60`                             |
| `--exclude-frozen`       | Skip products mentioning frozen/freezer                                  | off                              |
| `--exclude-keywords`     | Skip products whose title or marketing contains any of these terms       | none                             |
| `--title-only`           | Match keywords against title only, not marketing text                    | off (auto-on for `produce`)      |
| `--include-no-nutrition` | Include items with no nutrition data (protein/calories returned as null) | off (auto-on for `produce`)      |
| `--data-file`            | Override path to JSONL                                                   | auto-detected                    |

## Constraints

### Balanced meal guidelines

Based on USDA Dietary Guidelines, FDA Daily Values, and Institute of Medicine AMDR for a healthy adult on a ~2,000 cal/day diet.

#### Targets per meal

| Macro / Nutrient | Breakfast | Lunch   | Dinner  |
| ---------------- | --------- | ------- | ------- |
| Calories         | 500–600   | 700–800 | 500–600 |
| Protein          | 20–35g    | 30–45g  | 30–45g  |
| Carbohydrates    | 50–75g    | 75–110g | 75–110g |
| Fat              | 15–25g    | 20–30g  | 20–30g  |
| Fiber            | ≥7g       | ≥7g     | ≥7g     |
| Sodium           | <800mg    | <800mg  | <800mg  |
| Added sugar      | <10g      | <10g    | <10g    |

> **Protein:** Use the **high-ceiling** bands above as the target for recommendations — aim toward the upper half of each meal’s protein range (e.g. ~30–35g breakfast, ~40–45g lunch/dinner) when calories, fiber, and sodium caps still work. When the user specifies a protein target (e.g. "40g+"), use that as the protein floor and still satisfy the other macro ranges above.

### Rules

1. **MUST run the query script before composing any plan.** Never invent products — only use items returned by the script.
2. **MUST satisfy all macro targets** for the requested meal type by combining 2–4 products. Check protein, carbs, fat, fiber, and calories together — not just protein alone.
3. **Prefer fresh and refrigerated items over frozen.** Always pass `--exclude-frozen` unless the user explicitly asks to include frozen products.
4. **Primary output is the grocery list.** The meal plan table is secondary context.
5. **Vary macronutrient sources across days** — rotate protein types (poultry, beef, fish, legumes, dairy) and carb sources (grains, legumes, produce).
6. **Think in meal concepts, not ingredient lists.** Every meal must be a real, recognizable dish — not just a protein stacked next to a carb. Plan around formats people actually cook: tacos, stir-fries, pasta dishes, grain bowls with toppings, sheet pan dinners, smash burgers, BBQ plates, curry over rice, etc. The products should play natural culinary roles in that dish (e.g., birria as the filling in tacos, meatballs simmered in sauce over pasta, pulled chicken piled on a bun or rice bowl). If a product combination wouldn't make sense on a restaurant menu or a home cook's weeknight table, pick a different combination.
7. **Maximize ingredient sharing across meals.** Every plan should reuse at least 2–3 products across multiple meals — e.g., the same pulled chicken in a rice bowl for lunch and as taco filling for dinner, or the same bread used for lox toast at breakfast and a sandwich at lunch. Ingredient sharing reduces grocery waste, lowers total cost, and keeps the list shorter. When composing the plan, actively look for shared ingredients and design meals around them. Call out shared items explicitly in the grocery list (single line, combined quantity).
8. **Invent original recipes — do not default to Trader Joe's marketed uses.** Product copy and [EXAMPLES.md](references/EXAMPLES.md) calibrate quality; they are not a menu to copy. A product labeled "shawarma chicken" need not become "shawarma over rice" — it could fill a quesadilla, a grain bowl, or a pita. Optimize for unexpected but sound combinations.
