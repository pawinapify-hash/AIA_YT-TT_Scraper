# New Format Implementation Tasks

Migrate `bot.py` from old `col_values(2)` row-based config to `Google_Sheet_Data_Mapping.md` column-per-platform matrix.

---

## 1. Add Sheet Layout Constants

At top of `bot.py` (after env vars, before function definitions), define all cell coordinates as named constants:

- `CFG_RANGE = 'B1:F14'` — full config block fetched in one batch
- `PLATFORM_COL_INDEX` — `{name: gspread_col_number}` for columns B–F
- Platform row constants: `ROW_STATUS=5`, `ROW_KEYWORDS=6`, `ROW_TIME_FILTER=7`, `ROW_MAX_RESULTS=9`, `ROW_BUDGET=10`, `ROW_REMAINING=11`
- Global cell constants: `CELL_SYS_STATUS='D1'`, `CELL_OVERALL_BUDGET='D2'`, `CELL_OVERALL_REMAIN='D3'`, `CELL_LAST_ALERT='D12'`, `CELL_LAST_RESET='D13'`, `CELL_STATUS_LOG='D14'`
- Note: Row 8 (Interval) is defined in the sheet mapping but **not read by code** (dead since Colab removal).

## 2. New `read_platform_configs(ws_control)` Function

- Reads `ws_control.range('B1:F14')` in one batch API call
- Extracts global values: `D1` (status), `D2` (overall budget cap), `D3` (overall remaining), `D13` (last reset date)
- Iterates columns B–F; for each platform parses Row 5–11 into a config dict
- Only returns platforms where Row 5 == `'🟢 Start'`
- Budget fallback: if Row 10 is blank/null → use `D2` overall cap; if Row 11 is blank/null → use computed cap
- Converts Row 7 time filter: `1` → 1 day, `2` → 7 days, `3` → 30 days
- Returns `(global_config: dict, platform_configs: dict)`

## 3. Refactor `fetch_data()` — Single Platform

Old signature:
```python
fetch_data(platforms, keywords, max_res, days_back, budget_remaining)
```
→ iterated all platforms × keywords, returned `(all_videos, budget_remaining)`.

New signature:
```python
fetch_data(plat_name, keywords, max_results, days_back, plat_budget_remaining, overall_remaining)
```
→ handles **one platform at a time**, returns `(videos, plat_budget_remaining, overall_remaining)`.

Behavior:
- YouTube: skips budget checks entirely, uses `YOUTUBE_API_KEYS` as before
- Apify platforms: checks both `plat_budget_remaining >= cost` and `overall_remaining >= cost` before actor call; deducts from **both** on success
- All other scraping logic (Apify actor call, `normalize_apify_item`, result parsing) stays unchanged

## 4. Update `main()` — Config Reading

Replace:
```python
config = ws_control.col_values(2)
status = str(config[0]).strip()
platforms = [p.strip() for p in config[1].split(',')]
keywords = [k.strip() for k in config[2].split(',')]
days_back = ...
max_res = int(config[6]) if ...
budget_limit = float(config[7]) if ...
budget_remaining = float(config[8]) if ...
```

With:
```python
global_cfg, platform_configs = read_platform_configs(ws_control)
status = global_cfg['status']
overall_budget = global_cfg['overall_budget']
overall_remaining = global_cfg['overall_remaining']
```

- Status check becomes: `if 'Stop' not in status: break` — supports old format compatibility
- `platforms` list derived from `platform_configs.keys()`
- `keywords` are per-platform (pulled from each config entry in the loop)

## 5. Update `main()` — Fetch Loop

Replace the single `raw_list, budget_remaining = fetch_data(...)` call with a per-platform loop:
```python
all_raw = []
for plat_name, cfg in platform_configs.items():
    kws = [k.strip() for k in cfg['keywords'].split(',') if k.strip()]
    videos, cfg['budget_remaining'], overall_remaining = fetch_data(
        plat_name, kws, cfg['max_results'], cfg['days_back'],
        cfg['budget_remaining'], overall_remaining
    )
    all_raw.extend(videos)
```

## 6. Update `check_and_reset_daily_budget()`

- Reads last reset date from `CELL_LAST_RESET` (`D13`) instead of old `(12, 2)`
- On reset: writes to `CELL_OVERALL_REMAIN` (`D3`) for global + all `{col}11` cells for per-platform remaining budgets
- Writes reset date to `CELL_LAST_RESET` (`D13`)
- Returns updated `(overall_remaining, platform_configs_with_reset_budgets)`

## 7. Update Cell Writes After Fetch

After dedup and sheet write, persist budget state:
- Write `overall_remaining` to `CELL_OVERALL_REMAIN` (`D3`)
- For each active platform, write its `budget_remaining` to the corresponding row 11 cell
- Use `ws_control.batch_update()` to minimize API calls

## 8. Rename `update_heartbeat()` → `update_status_log()`

- Writes current timestamp to `CELL_STATUS_LOG` (`D14`) instead of old `(11, 2)`
- Called once per cycle at the start of the loop (same behavior as before)

## 9. Notification Logic

No changes. Google Chat webhooks fire as before. TikTok-specific webhook still triggers when TikTok is in the active platform set.

## 10. Update Tests

- `tests/test_status_control.py`: update expected cell coordinates to match new layout
- `tests/test_platform_config.py`: should still pass unchanged (actor configs are untouched)

---

## Files Touched

| File | Scope |
|---|---|
| `bot.py` | ~80% of `main()` rewritten; new `read_platform_configs()`; updated `fetch_data()`; updated `check_and_reset_daily_budget()`; `update_heartbeat` → `update_status_log`; constants block added |
| `platform_config.py` | No changes |
| `apify_result_parser.py` | No changes |
| `tests/test_status_control.py` | Update cell coordinate assertions |

---

## Status

- [x] 1. Add sheet layout constants
- [x] 2. New `read_platform_configs()` function
- [x] 3. Refactor `fetch_data()` to single-platform
- [x] 4. Update config reading in `main()`
- [x] 5. Update fetch loop in `main()`
- [x] 6. Update `check_and_reset_daily_budget()`
- [x] 7. Update post-fetch cell writes
- [x] 8. Rename heartbeat → status log
- [x] 9. Notification logic (verified, no changes)
- [x] 10. Update tests
