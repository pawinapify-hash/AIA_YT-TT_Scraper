# AIA Social Media Scraper

## Overview
Automated social media scraper that searches for new posts on YouTube, TikTok, Instagram, Facebook, and LinkedIn, then writes results to a Google Sheet with deduplication. Sends summary notifications to Google Chat webhooks.

## How it works

1. Reads platform and keyword configuration from the `Control_Panel` worksheet in Google Sheets
2. Searches **YouTube** via the YouTube Data API v3
3. Searches **TikTok, Instagram, Facebook, LinkedIn** via Apify actors with budget tracking
4. Deduplicates results against previously logged URLs in the `Apify` worksheet
5. Writes new posts to the `Apify` worksheet (columns: date, title, platform, user, URL, timestamp)
6. Logs scan summaries to the `Scan_Logs` worksheet
7. Sends Google Chat notifications for new posts (general webhook + TikTok-specific webhook)
8. Tracks a daily Apify API budget with automatic reset at midnight (Bangkok time)

## Run modes

- **Continuous** (Colab): loops indefinitely with a configurable interval between iterations
- **Run Once** (GitHub Actions / serverless): executes one cycle, writes status to Control_Panel, then exits

## Environment variables

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEYS` | Comma-separated YouTube Data API v3 keys |
| `APIFY_TOKENS` | Comma-separated Apify API tokens |
| `SHEET_ID` | Google Sheets spreadsheet ID |
| `CREDENTIALS_JSON` | Service account JSON for Google Sheets auth |

## Google Sheet structure

| Worksheet | Purpose |
|-----------|---------|
| `Control_Panel` | Column B: status, platforms, keywords, time window, run mode, interval, max results, budget limit |
| `Apify` | Stores scraped results — date, title, platform, user, URL, timestamp |
| `Scan_Logs` | Auto-created; logs timestamp, duplicates, new items, platforms per batch |

## Repository files

| File | Purpose |
|------|---------|
| `bot.py` | Main entry point — auto-installs deps, scrapes, deduplicates, writes to sheets, notifies |
| `platform_config.py` | Apify actor configurations per platform (TikTok, Instagram, Facebook, LinkedIn) |
| `apify_result_parser.py` | Normalizes raw Apify API responses to a consistent format |
| `tests/` | Unit tests for parsers, configs, and helpers |

## Dependencies

Installed automatically at runtime: `yt-dlp`, `apify-client`, `gspread`

CI also installs: `google-api-python-client`, `google-auth-oauthlib`

## Usage

```bash
python bot.py
```

## CI/CD

GitHub Actions workflow (`.github/workflows/main.yml`) triggers via `repository_dispatch` from Google Apps Script or manual `workflow_dispatch`.
