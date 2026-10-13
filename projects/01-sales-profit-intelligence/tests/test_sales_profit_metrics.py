"""Tests for the sales metrics module; run with python -B -m unittest discover -s tests."""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.sales_profit_metrics import (  # noqa: E402
    DataValidationError,
    aggregate_monthly_metrics,
    aggregate_metrics,
    calculate_metrics,
    format_percent,
    load_sales_data,
    round_currency,
    summarize_metrics,
)


class SalesProfitMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_sales_data()

    @staticmethod
    def sample_row() -> dict[str, object]:
        return {
            "order_date": "2025-01-15",
            "product": "Sample Product",
            "category": "Sample Category",
            "region": "Sample Region",
            "units_sold": "2",
            "unit_price": "10.00",
            "unit_cost": "4.00",
            "discount_rate": "0.10",
        }

    def test_verified_overall_csv_totals(self) -> None:
        summary = summarize_metrics(self.data)
        self.assertEqual(summary["record_count"], 49)
        self.assertEqual(summary["units_sold"], 890)
        self.assertEqual(summary["revenue_after_discounts"], Decimal("39074.47"))
        self.assertEqual(summary["recorded_product_cost"], Decimal("22642.90"))
        self.assertEqual(summary["calculated_profit"], Decimal("16431.57"))
        self.assertEqual(
            summary["profit_margin"].quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
            Decimal("0.421"),
        )

    def test_half_up_rounding_resolves_accessories_tie(self) -> None:
        exact_tie = Decimal("7402.825")
        self.assertEqual(round_currency(exact_tie), Decimal("7402.83"))
        self.assertEqual(round_currency(Decimal("7402.8249")), Decimal("7402.82"))
        self.assertEqual(round_currency(Decimal("-1.235")), Decimal("-1.24"))
        self.assertEqual(format_percent(Decimal("0.503120")), "50.3%")
        self.assertEqual(format_percent(Decimal("0.629909")), "63.0%")
        self.assertEqual(format_percent(None), "N/A")

        category = aggregate_metrics(self.data, "category").set_index("category")
        self.assertEqual(
            category.loc["Accessories", "calculated_profit"], Decimal("7402.83")
        )
        # The previous executed output displayed 7402.82 for this exact half-cent;
        # retain this assertion to guard the canonical HALF_UP policy.
        self.assertNotEqual(
            category.loc["Accessories", "calculated_profit"], Decimal("7402.82")
        )

    def test_product_category_region_and_month_aggregations(self) -> None:
        product = aggregate_metrics(self.data, "product").set_index("product")
        category = aggregate_metrics(self.data, "category").set_index("category")
        region = aggregate_metrics(self.data, "region").set_index("region")
        month = aggregate_metrics(self.data, "month")

        self.assertEqual(product.loc["Monitor 24in", "calculated_profit"], Decimal("3509.75"))
        self.assertEqual(product.loc["Notebook Pack", "revenue_after_discounts"], Decimal("2504.53"))
        self.assertEqual(product.loc["Notebook Pack", "calculated_profit"], Decimal("1577.63"))
        self.assertNotEqual(product.loc["Notebook Pack", "calculated_profit"], Decimal("1577.62"))
        self.assertEqual(category.loc["Accessories", "revenue_after_discounts"], Decimal("14713.83"))
        self.assertEqual(category.loc["Accessories", "calculated_profit"], Decimal("7402.83"))
        self.assertEqual(category.loc["Stationery", "revenue_after_discounts"], Decimal("2504.53"))
        self.assertEqual(category.loc["Stationery", "calculated_profit"], Decimal("1577.63"))
        self.assertEqual(category.index[0], "Accessories")
        self.assertEqual(region.loc["North", "calculated_profit"], Decimal("4560.56"))
        self.assertEqual(product.index[0], "Monitor 24in")
        self.assertEqual(region.index[0], "North")
        self.assertEqual(int(month["record_count"].sum()), 49)
        self.assertEqual(int(month["units_sold"].sum()), 890)
        self.assertTrue(month["month"].str.fullmatch(r"\d{4}-\d{2}").all())

    def test_monthly_trend_aggregation_is_chronological(self) -> None:
        profit_ranked_months = aggregate_metrics(self.data, "month")["month"].tolist()
        chronological_months = aggregate_monthly_metrics(self.data)["month"].tolist()

        self.assertEqual(chronological_months, sorted(chronological_months))
        self.assertNotEqual(chronological_months, profit_ranked_months)

    def test_missing_columns_are_rejected(self) -> None:
        row = self.sample_row()
        frame = pd.DataFrame([row]).drop(columns=["discount_rate"])
        with self.assertRaisesRegex(DataValidationError, "discount_rate"):
            calculate_metrics(frame)

    def test_empty_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(DataValidationError, "empty"):
            calculate_metrics(pd.DataFrame(columns=list(self.sample_row())))

    def test_invalid_date_is_rejected(self) -> None:
        row = self.sample_row()
        row["order_date"] = "not-a-date"
        with self.assertRaisesRegex(DataValidationError, "order_date"):
            calculate_metrics(pd.DataFrame([row]))

    def test_invalid_numeric_values_are_rejected(self) -> None:
        cases = (
            ("unit_price", "not-a-number"),
            ("units_sold", "-1"),
            ("units_sold", "1.5"),
            ("unit_cost", "-0.01"),
            ("discount_rate", "1.01"),
            ("discount_rate", "-0.01"),
            ("unit_price", ""),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                row = self.sample_row()
                row[field] = value
                with self.assertRaises(DataValidationError):
                    calculate_metrics(pd.DataFrame([row]))

    def test_missing_dimension_value_is_rejected(self) -> None:
        row = self.sample_row()
        row["product"] = "  "
        with self.assertRaisesRegex(DataValidationError, "product"):
            calculate_metrics(pd.DataFrame([row]))

    def test_zero_revenue_has_no_undefined_or_infinite_margin(self) -> None:
        row = self.sample_row()
        row.update(unit_price="10.00", unit_cost="4.00", discount_rate="1")
        calculated = calculate_metrics(pd.DataFrame([row]))
        self.assertEqual(calculated.loc[0, "revenue_after_discounts"], Decimal("0.00"))
        self.assertEqual(calculated.loc[0, "calculated_profit"], Decimal("-8.00"))
        self.assertIsNone(calculated.loc[0, "profit_margin"])

        grouped = aggregate_metrics(pd.DataFrame([row]), "category")
        self.assertIsNone(grouped.loc[0, "profit_margin"])

    def test_unsupported_grouping_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported grouping"):
            aggregate_metrics(self.data, "customer")


if __name__ == "__main__":
    unittest.main()
