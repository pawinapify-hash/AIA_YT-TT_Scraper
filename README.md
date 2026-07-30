# Logo Hunter Bot

## Overview
This repository contains a single-script monitoring bot for automated social media scanning and logo detection. It searches for new posts on YouTube, TikTok, Instagram, and Facebook, analyzes the content for logo appearances, and writes results to a Google Sheet. When a logo is detected, the bot can also upload evidence images and send summary notifications.

The main use case is keyword-based monitoring, deduplication of previously seen posts, and logging new content while avoiding older items.

## What the bot does
- Reads platform and keyword configuration from a Google Sheet.
- Uses the YouTube Data API for YouTube searches.
- Uses Apify actors to scrape TikTok, Instagram, and Facebook search results.
- Detects whether a logo is present in frames or thumbnails using a local PyTorch model when available.
- Saves evidence images through ImgBB, Google Drive, or fallback services such as Catbox and Tmpfiles.
- Logs results to a Google Sheet with metadata such as URL, title, user, platform, detection result, and timestamp.
- Sends summary updates to Google Chat webhooks.
- Supports execution in a GitHub-style environment as well as Colab-style setups.

## Repository files
### `bot.py`
This is the main and only application file in the repository. It contains:
- dependency installation and imports
- Google Sheets and Drive authentication
- environment-based API key loading
- text sanitizing, notification, and heartbeat helpers
- the main fetch logic for YouTube, TikTok, Instagram, and Facebook
- deduplication logic and old-content filtering
- AI model loading and logo prediction
- evidence-image upload and fallback handling
- batch insertion into the Google Sheet
- the repeated execution loop and configuration handling

### `.git/` and `.github/`
These are repository metadata directories created by Git and GitHub. They are not part of the bot logic itself, but may contain version history and workflow configuration.

## Required files and assets
- `bigc_model.pth`
  - Optional local AI model file used for logo detection. If it is missing, the bot will still run but skip image/video logo analysis.

## Environment variables
The bot reads configuration from environment variables. The most important ones are:
- `YOUTUBE_API_KEYS`
  - Comma-separated YouTube API keys used for YouTube search queries.
- `APIFY_TOKENS`
  - Comma-separated Apify API tokens used for TikTok, Instagram, and Facebook scrapers.
- `SHEET_ID`
  - The Google Sheets ID where the bot writes results and reads control values.
- `GDRIVE_FOLDER_ID`
  - Optional Google Drive folder ID for image upload storage.
- `IMGBB_API_KEY`
  - Optional ImgBB upload key. If provided, the bot attempts to upload evidence images to ImgBB first.
- `CREDENTIALS_JSON`
  - Required service-account JSON content for Google Sheets and Google Drive authentication.

## How to run
1. Place `bot.py` and optionally `bigc_model.pth` in the same folder.
2. Set the required environment variables, especially `CREDENTIALS_JSON` and `SHEET_ID`.
3. Run the script:

```bash
python bot.py
```

## How the bot is configured
The bot expects a Google Sheet with at least these worksheets:
- `Apify`
  - Used for storing scanned results and metadata.
- `Control_Panel`
  - Used for runtime configuration such as start/stop status, platform list, keywords, time filter, interval, run mode, and max results.
- `Scan_Logs`
  - Created automatically if missing and used for log history.

## Notes
- The project currently consists of a single Python script: `bot.py`.
- The bot installs its Python dependencies automatically at runtime if they are missing.
- If the AI model file is absent, the bot still runs but skips logo detection.
- The script includes fallback upload support so evidence images can still be shared even if primary upload services fail.

## Summary
This repository is a monitoring bot that combines social media search, deduplication, AI-based logo detection, and Google Sheet logging. The full application logic is implemented in `bot.py`, and this README documents its current setup, configuration, and behavior.
