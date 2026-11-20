"""Unit tests for the GitHub statistics generator."""
import datetime as dt
import unittest
from collections import Counter
from xml.etree import ElementTree

import generate_stats as stats


class StreakTests(unittest.TestCase):
    def test_current_and_longest_streak(self):
        today = dt.date(2026, 11, 20)
        days = {
            "2026-11-15": 1,
            "2026-11-16": 2,
            "2026-11-17": 0,
            "2026-11-18": 1,
            "2026-11-19": 1,
            "2026-11-20": 3,
        }
        current, longest = stats.streaks(days, today=today)
        self.assertEqual(current, (3, "2026-11-18", "2026-11-20"))
        self.assertEqual(longest, (3, "2026-11-18", "2026-11-20"))

    def test_streak_ending_yesterday_is_current(self):
        today = dt.date(2026, 11, 20)
        days = {"2026-11-18": 1, "2026-11-19": 1}
        current, _ = stats.streaks(days, today=today)
        self.assertEqual(current, (2, "2026-11-18", "2026-11-19"))

    def test_old_streak_is_not_current(self):
        today = dt.date(2026, 11, 20)
        days = {"2026-11-15": 1, "2026-11-16": 1}
        current, longest = stats.streaks(days, today=today)
        self.assertEqual(current, (0, None, None))
        self.assertEqual(longest[0], 2)


class PercentageTests(unittest.TestCase):
    def test_percentage_rows_include_other(self):
        rows = stats.pct_rows(Counter({"Python": 60, "JavaScript": 30, "Go": 10}), n=2)
        self.assertEqual(rows, [("Python", 60.0), ("JavaScript", 30.0), ("Other", 10.0)])

    def test_empty_counter_is_safe(self):
        self.assertEqual(stats.pct_rows(Counter()), [])

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            stats.pct_rows(Counter({"Python": 1}), n=0)

    def test_negative_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            stats.pct_rows(Counter({"Python": -1}))


class RenderingTests(unittest.TestCase):
    def test_sample_pipeline_produces_valid_svg(self):
        base, days, repos = stats.sample_data()
        analysis = stats.analyse(base, days, repos)
        svg = stats.render(base, analysis, sample=True)
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertIn("PREVIEW: SAMPLE DATA", svg)
        self.assertIn("contributions", svg)

    def test_dynamic_profile_text_is_escaped(self):
        base, days, repos = stats.sample_data()
        base["name"] = "Example <script>alert(1)</script>"
        analysis = stats.analyse(base, days, repos)
        svg = stats.render(base, analysis, sample=True)
        self.assertIn("&lt;script&gt;", svg)
        self.assertNotIn("<script>", svg)


if __name__ == "__main__":
    unittest.main()
