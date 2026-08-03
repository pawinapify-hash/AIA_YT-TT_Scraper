from datetime import datetime, timedelta, timezone


def get_apify_actor_config(platform, keyword, max_results, time_window_days=None):
    """Return the Apify actor name and input payload for a platform."""
    if platform == "TikTok":
        clean_kw = keyword.replace("#", "").strip()
        payload = {
            "maxItems": max_results,
            "resultsPerPage": max_results,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        if keyword.startswith("#"):
            payload["hashtags"] = [clean_kw]
        else:
            payload["searchQueries"] = [keyword]
        return "clockworks/tiktok-scraper", payload

    if platform == "Instagram":
        payload = {
            "hashtags": [keyword.replace("#", "").replace(" ", "")],
            "resultsLimit": max_results,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        return "apify/instagram-hashtag-scraper", payload

    if platform == "Facebook":
        payload = {
            "searchTerms": keyword,
            "resultsLimit": max_results,
            "maxItems": max_results,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        return "apify/facebook-search-scraper", payload

    if platform == "LinkedIn":
        payload = {
            "contentType": "all",
            "maxPosts": max_results,
            "postNestedComments": False,
            "postNestedReactions": False,
            "scrapeComments": False,
            "scrapeReactions": False,
            "searchQueries": [keyword],
            "sortBy": "relevance",
        }
        if time_window_days is None:
            time_window_days = 30

        if time_window_days == 1:
            days_back = 1
        elif time_window_days == 2:
            days_back = 7
        else:
            days_back = 30

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date().isoformat()
        payload["postedLimitDate"] = cutoff_date
        return "harvestapi/linkedin-post-search", payload

    return "", {}
