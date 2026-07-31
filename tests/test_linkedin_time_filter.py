import unittest
from datetime import datetime, timedelta, timezone

from platform_config import get_apify_actor_config


class LinkedInTimeFilterTests(unittest.TestCase):
    def test_linkedin_payload_uses_posted_limit_date_for_day_filter(self):
        expected_date = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        _, payload = get_apify_actor_config("LinkedIn", "AI", 20, 1)
        self.assertEqual(payload["postedLimitDate"], expected_date)

    def test_linkedin_payload_uses_posted_limit_date_for_week_filter(self):
        expected_date = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        _, payload = get_apify_actor_config("LinkedIn", "AI", 20, 2)
        self.assertEqual(payload["postedLimitDate"], expected_date)

    def test_linkedin_payload_uses_posted_limit_date_for_month_filter(self):
        expected_date = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        _, payload = get_apify_actor_config("LinkedIn", "AI", 20, 30)
        self.assertEqual(payload["postedLimitDate"], expected_date)


if __name__ == "__main__":
    unittest.main()
