# Apify LinkedIn Post Scraper - Parameter Reference
harvestapi/linkedin-post-search

Summary of input parameters and configuration options for the Apify Actor.

---

## 1. Search & Scraping Scope

| Field Name | Parameter Key (`json`) | Required / Optional | Type | Limits / Default | Options / Format | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Search queries** | `searchQueries` | Optional | `array` | Max 10,000 items | Text string | Search terms as you would type them in the LinkedIn search bar. |
| **Max Posts per Query** | `maxPosts` | Optional | `integer` | Default: `0` (unlimited) | `0` or greater | Maximum posts to scrape per query. Set to `0` to scrape all available posts. |
| **Start Page** | `startPage` | Optional | `integer` | Min: `1`, Max: `100`<br>Default: `1` | `1`–`100` | Search page number to start scraping from. |
| **Pages to Scrape** | `scrapePages` | Optional | `integer` | Min: `0`, Max: `100` | `0`–`100` | Number of search pages to scrape (each page contains ~100 posts). |

---

## 2. Filters & Targeting

### Date & Sorting Filters
| Field Name | Parameter Key (`json`) | Required / Optional | Type | Options / Format | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Posted Limit** | `postedLimit` | Optional | `string` | `any`, `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year` | Fetch posts published within a specific relative timeframe. |
| **Posted Limit Date** | `postedLimitDate` | Optional | `string` | ISO 8601 (`"2011-10-10"`, `"2011-10-10T14:48:00.000+09:00"`) or Unix timestamp (`"628021800000"`) | Scrape posts from now up to and including this cutoff date/time. |
| **Sort By** | `sortBy` | Optional | `string` | `relevance`, `date` | Sort search results by relevance or recency. |

### Author & Content Filters
| Field Name | Parameter Key (`json`) | Required / Optional | Type | Limits / Default | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Profile or Company URLs** | `authorUrls` | Optional | `array` | Max 10 items | List of profile or company URLs (e.g., `https://www.linkedin.com/in/williamhgates`) to fetch content from. |
| **Authors Companies** | `authorsCompanies` | Optional | `array` | Max 20 items | List of company names (e.g., `Google`) to scrape posts from current or past employees. |
| **Mentioning Member** | `mentioningMember` | Optional | `array` | Max 10 items | Scrape posts mentioning specific member profiles. |
| **Mentioning Company** | `mentioningCompany` | Optional | `array` | — | Scrape posts mentioning specific LinkedIn company pages. |
| **Content Type** | `contentType` | Optional | `string` | — | Filter by post type. **Options:** `all`, `videos`, `images`, `jobs`, `live_videos`, `documents`, `collaborative_articles`. |
| **Authors Industry ID** | `authorsIndustryId` | Optional | `array` | Max 20 items | Scrape posts by authors belonging to specific [LinkedIn Industry Codes](https://github.com/HarvestAPI/linkedin-industry-codes-v2/blob/main/linkedin_industry_code_v2_all_eng.csv). |
| **Author Keywords** | `authorKeywords` | Optional | `string` | — | Filter authors whose headline or job title contains at least one of these keywords. |

---

## 3. Profile & Data Extraction Settings

| Field Name | Parameter Key (`json`) | Required / Optional | Type | Options / Default | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Profile Scraper Mode** | `profileScraperMode` | Optional | `string` | `short` (Default), `main` | Defines depth of scraped profile data (`short` = basic info, `main` = full profile data). |

---

## 4. Reactions & Comments Settings

### Reactions Configuration
| Field Name | Parameter Key (`json`) | Type | Options / Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Scrape Reactions** | `scrapeReactions` | `boolean` | `true` / `false` | Enable/disable scraping post reactions. |
| **Max Reactions** | `maxReactions` | `integer` | Default: `10` | Max reactions to scrape per individual post. |
| **Reactions Profile Scraper Mode** | `reactionsProfileScraperMode` | `string` | `short` (Default), `main` | Detail level of profiles for users who reacted. |
| **Post Nested Reactions** *(Legacy)* | `postNestedReactions` | `boolean` | `true` / `false` | **Not recommended.** Nesting reactions inside the post payload can cause items to exceed Apify size limits. |

### Comments Configuration
| Field Name | Parameter Key (`json`) | Type | Options / Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Scrape Comments** | `scrapeComments` | `boolean` | `true` / `false` | Enable/disable scraping post comments. |
| **Comments Posted Limit** | `commentsPostedLimit` | `string` | `any`, `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year` | Filter comments published within a specific timeframe. |
| **Max Comments** | `maxComments` | `integer` | Default: `10` | Max comments to scrape per individual post. |
| **Comments Profile Scraper Mode** | `commentsProfileScraperMode` | `string` | `short` (Default), `main` | Detail level of profiles for users who commented. |
| **Post Nested Comments** *(Legacy)* | `postNestedComments` | `boolean` | `true` / `false` | **Not recommended.** Nesting comments inside the post payload can cause items to exceed Apify size limits. |

---
# Sample Parameter
{
    "contentType": "all",
    "maxPosts": 20,
    "postNestedComments": false,
    "postNestedReactions": false,
    "postedLimitDate": "2026-07-24",
    "scrapeComments": false,
    "scrapeReactions": false,
    "searchQueries": [
        "เอไอเอ"
    ],
    "sortBy": "relevance"
}