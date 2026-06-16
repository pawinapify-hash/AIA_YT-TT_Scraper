# Logo Hunter Bot

## Overview
This project is a single-script bot for automated social media monitoring and logo detection. It searches for new video posts on platforms such as YouTube, TikTok, Instagram, and Facebook, then analyzes the content to detect logo appearances. When logos are detected, the bot stores a record in a Google Sheet and optionally uploads evidence images through ImgBB, Google Drive, or fallback services.

The main use case is monitoring keyword-based social media content and logging new posts while avoiding duplicates and older content.

## What this project does
- Reads platform and keyword configuration from a Google Sheet.
- Uses the YouTube Data API for YouTube searches.
- Uses Apify actors to scrape TikTok, Instagram, and Facebook search results.
- Detects whether a logo is present in video frames or post thumbnails using a local PyTorch model.
- Saves evidence images using ImgBB, Google Drive, or fallback upload services (Catbox / Tmpfiles).
- Logs results to a Google Sheet and stores metadata such as URL, title, user, platform, detection result, and timestamp.
- Sends summary notifications to Google Chat webhooks.
- Supports both serverless GitHub-style runs and Colab-style interactive authentication.

## Files in this repository
### `bot.py`
This is the main and only application file in the repository. It contains:
- dependency installation and imports
- Google Sheets and Drive authentication
- API key loading from environment variables
- functions for formatting and sanitizing text, sending notifications, and updating a heartbeat timestamp
- the main fetch logic for YouTube, TikTok, Instagram, and Facebook
- logic for deduplicating posts and skipping old content
- AI model loading and logo prediction on video frames or images
- evidence image upload and fallback handling
- batch insertion into the Google Sheet
- repeated execution loop and configuration handling

### `.git/` and `.github/`
These are repository metadata directories created by Git and GitHub. They are not part of the application logic, but store version control history and GitHub workflow configuration if present.

## Required files and assets
- `credentials.json`
  - Needed for Google Sheets and Google Drive service account authentication.
- `bigc_model.pth`
  - Optional local AI model file used for logo detection.

## Environment variables
The bot reads configuration from environment variables. The most important ones are:
- `YOUTUBE_API_KEYS`
  - Comma-separated YouTube API keys used for YouTube search queries.
- `APIFY_TOKENS`
  - Comma-separated Apify API tokens used for TikTok/Instagram/Facebook scrapers.
- `SHEET_ID`
  - The Google Sheets ID where the bot writes results and reads control values.
- `GDRIVE_FOLDER_ID`
  - Optional Google Drive folder ID for image upload storage.
- `IMGBB_API_KEY`
  - Optional ImgBB upload key. If provided, the bot uploads evidence images to ImgBB first.

## How to run
1. Place `bot.py`, `credentials.json`, and optionally `bigc_model.pth` in the same folder.
2. Set the required environment variables.
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
  - Created automatically if missing, used to store log history.

## Notes
- The project currently consists of a single Python script: `bot.py`.
- The bot installs its Python dependencies automatically at runtime if they are missing.
- If the AI model file is absent, the bot will still run but skip video/image logo detection.
- The script includes fallback upload support so evidence images can still be shared even if primary upload services fail.

## Summary
This repository is a monitoring bot that combines social media search, deduplication, AI-based logo detection, and Google Sheet logging. The entire app is implemented in `bot.py`, and the README documents the setup, configuration, and behavior of the bot.
