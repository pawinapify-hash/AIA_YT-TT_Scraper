# Task: Add `budget_limit` to control Apify usage

## Goal
Add a new configuration variable `budget_limit` (read from `Control_Panel` Google Sheet below `max_res` at `config[7]`) and use it to prevent further Apify API calls once the daily budget is exhausted.

## Design / Process Flow
1. Read `budget_limit` from the `Control_Panel` worksheet using `config[7]` (after `max_res`). If missing or invalid, default to integer `3` (USD/day).
2. Initialize an in-memory counter `budget_remaining` at the start of each run set to `budget_limit`.
3. For each Apify actor call, compute an estimated cost using: `estimated_cost = max_results * per_item_rate` and check `budget_remaining` before calling Apify. If the remaining budget is less than the estimated cost, skip the Apify call and log the skip.
    - Default `per_item_rate` is ~`0.004` USD per result (derived from 15 results → $0.06 total). This makes estimated cost for `max_res=15` be ~`0.06` USD.
4. When budget is exhausted, stop making Apify calls for the remainder of the run, but continue processing any items already fetched.
5. Optionally persist the remaining budget back to the `Control_Panel` sheet so subsequent runs can resume with the remaining budget (requires write permission).

## Implementation Steps
- Code changes in `bot.py`:
    - Parse `budget_limit` from `config[7]` after `max_res` and coerce to `int` with a safe fallback to `3`.
    - Set `budget_remaining = float(budget_limit)` at run start.
    - Define `per_item_rate = 0.004` (USD) by default; allow an optional override via code or sheet.
    - In `fetch_data`, before making an Apify actor call, compute `estimated_cost = max_res * per_item_rate` and check `if budget_remaining < estimated_cost: skip and log`.
    - After approving the call, deduct the estimated cost: `budget_remaining -= estimated_cost`.
  - Add logging lines when skipping due to budget exhaustion.
  - (Optional) Persist `budget_remaining` back to `Control_Panel` via `ws_control.update_cell()` (choose a designated cell column).

## User-visible behavior
- New `Control_Panel` integer column `budget_limit` (placed below `max_res` and read as `config[7]`). If omitted or invalid, the bot uses the default `3` (USD/day).
- Today's Remaining Budget cell is `config[8]` (row 9 in column B) and will be updated each run with the current `budget_remaining`.
- `Last System Alert` maps to `config[12]` (row 13 in column B) per your sheet layout; use it for alert messages.
- When budget is exhausted, the bot will stop calling Apify scrapers and only rely on other configured platforms (e.g., YouTube).

## Notes and Assumptions
- The default budget is `3` (USD/day) and the estimated Apify cost is calculated as `max_res * 0.004` USD.
- Persisting budget across runs requires the service account to have edit permissions on the sheet.

## Implementation status
- Budget config read from `config[7]` is implemented.
- Remaining budget is read from `config[8]` and written back to the sheet at row 9, column B.
- Apify call skipping and cost deduction are implemented using the `APIFY_RATE_PER_RESULT` rate.

Example snippet (current implementation):

```python
# budget_limit is expected at config[7]; default to 3 if missing/invalid
try:
    budget_limit = int(config[7]) if len(config) > 7 and str(config[7]).strip().isdigit() else 3
except:
    budget_limit = 3

budget_remaining = budget_limit
cost_per_apify_call = 1
```

And in `fetch_data()` before calling Apify actor:

```python
if budget_remaining < cost_per_apify_call:
    print(f"  ⛔ Skipping Apify for {plat} due to budget exhausted ({budget_remaining}$ remaining)")
    continue
# else: make call and then deduct
budget_remaining -= cost_per_apify_call
```

If you want me to implement these changes now, confirm whether to use the flat `$1` per-call default or provide a custom per-actor cost map.

# Persisting budget back to Google Sheet (required)

At the end of each successful run (or just before the script exits when running serverless), write the current `budget_remaining` back to the `Control_Panel` so subsequent runs can continue with the updated remaining budget. The script reads config values from column B using `ws_control.col_values(2)`. `budget_limit` is expected at `config[7]` (row 8); store the running remaining budget into the separate cell `Today's Remaining Budget` at `config[8]` (row 9 in column B).

Example snippet to run at the end of the run or in a `finally` block:

```python
try:
    # ... main run logic ...
finally:
    try:
        # write remaining budget to row 9, column 2 (B9)
        ws_control.update_cell(9, 2, str(round(budget_remaining, 4)))
        print(f"🔄 Updated budget_remaining back to sheet: {budget_remaining}")
    except Exception as e:
        print(f"⚠️ Failed to persist budget_remaining to sheet: {e}")

```

Note: Persisting requires the service account to have edit permissions on the sheet. If you prefer not to overwrite those cells, we can instead create a dedicated log/metadata worksheet to store `budget_remaining` and timestamps.