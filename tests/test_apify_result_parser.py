import unittest

from apify_result_parser import normalize_apify_item
from datetime import datetime, timezone


class ApifyResultParserTests(unittest.TestCase):
    def test_linkedin_item_is_normalized(self):
        cutoff = datetime(2026, 7, 31, tzinfo=timezone.utc)
        item = {
            "id": "123",
            "content": "AI post",
            "author": {"name": "Jane Doe"},
            "createdAt": "2026-07-30T10:00:00Z",
            "url": "https://www.linkedin.com/feed/update/123"
        }
        normalized = normalize_apify_item(item, "LinkedIn", cutoff)
        self.assertEqual(normalized["platform"], "LinkedIn")
        self.assertEqual(normalized["title"], "AI post")
        self.assertEqual(normalized["user"], "Jane Doe")
        self.assertEqual(normalized["url"], "https://www.linkedin.com/feed/update/123")

    def test_linkedin_payload_example_is_normalized(self):
        cutoff = datetime(2026, 7, 31, tzinfo=timezone.utc)
        item = {
            "type": "post",
            "id": "7330988768578920448",
            "linkedinUrl": "https://www.linkedin.com/posts/nickbennett05_hiring-activity-7330988768578920448-Je01",
            "content": "I’m #hiring. Are you passionate about the intersection of physical and virtual worlds?",
            "author": {
                "name": "Nick Bennett",
                "publicIdentifier": "nickbennett05"
            },
            "postedAt": {
                "timestamp": 1747843925614,
                "date": "2025-05-21T16:12:05.614Z"
            },
            "socialContent": {
                "shareUrl": "https://www.linkedin.com/posts/nickbennett05_hiring-activity-7330988768578920448-Je01?utm_source=social_share_send"
            }
        }
        normalized = normalize_apify_item(item, "LinkedIn", cutoff)
        self.assertEqual(normalized["platform"], "LinkedIn")
        self.assertEqual(normalized["title"], "I’m #hiring. Are you passionate about the intersection of physical and virtual worlds?")
        self.assertEqual(normalized["user"], "Nick Bennett")
        self.assertEqual(normalized["url"], "https://www.linkedin.com/posts/nickbennett05_hiring-activity-7330988768578920448-Je01")


if __name__ == "__main__":
    unittest.main()
