import unittest

from platform_config import get_apify_actor_config


class PlatformConfigTests(unittest.TestCase):
    def test_linkedin_returns_configured_actor_and_payload(self):
        actor, payload = get_apify_actor_config("LinkedIn", "เอไอเอ", 20)
        self.assertEqual(actor, "harvestapi/linkedin-post-search")
        self.assertEqual(payload["searchQueries"], ["เอไอเอ"])
        self.assertEqual(payload["maxPosts"], 20)
        self.assertEqual(payload["sortBy"], "relevance")
        self.assertFalse(payload["scrapeComments"])
        self.assertFalse(payload["scrapeReactions"])

    def test_tiktok_payload_uses_search_queries_when_keyword_is_not_hashtag(self):
        actor, payload = get_apify_actor_config("TikTok", "python", 10)
        self.assertEqual(actor, "clockworks/tiktok-scraper")
        self.assertIn("searchQueries", payload)
        self.assertEqual(payload["searchQueries"], ["python"])


if __name__ == "__main__":
    unittest.main()
