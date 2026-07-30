def get_apify_actor_config(platform, keyword, max_results):
    """Return the Apify actor name and input payload for a platform.

    LinkedIn is intentionally left blank for now so the actor name and
    parameter payload can be filled in later without changing the flow.
    """
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
        return "harvestapi/linkedin-post-search", payload

    return "", {}
