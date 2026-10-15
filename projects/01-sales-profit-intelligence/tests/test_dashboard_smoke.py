"""Smoke tests for the interactive Streamlit dashboard."""

from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_starts_and_renders_core_sections(self) -> None:
        app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30).run()

        self.assertEqual(len(app.exception), 0, msg="; ".join(e.message for e in app.exception))
        self.assertEqual(app.title[0].value, "Sales & Profit Intelligence")

        metric_labels = {metric.label for metric in app.metric}
        self.assertTrue(
            {
                "Revenue After Discounts",
                "Recorded Product Cost",
                "Calculated Profit",
                "Profit Margin",
                "Units Sold",
                "Top Category by Calculated Profit",
                "Top Product by Calculated Profit",
                "Highest-Margin Product",
                "Top Region by Calculated Profit",
            }.issubset(metric_labels),
            msg=f"Unexpected dashboard metrics: {sorted(metric_labels)}",
        )

        section_titles = {element.value for element in app.subheader}
        self.assertTrue(
            {
                "Monthly Revenue and Calculated Profit",
                "Calculated Profit by Product",
                "Category Performance",
                "Regional Performance",
                "Business Highlights",
            }.issubset(section_titles),
            msg=f"Missing dashboard sections: {sorted(section_titles)}",
        )


if __name__ == "__main__":
    unittest.main()
