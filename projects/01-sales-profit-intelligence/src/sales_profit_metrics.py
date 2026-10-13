"""Validated, deterministic metrics for the synthetic sales dataset.

Money is calculated from the CSV's decimal text without per-row rounding.
Aggregated monetary values are rounded only at the reporting boundary to two
fractional digits using ROUND_HALF_UP (ties away from zero). The previous
notebook outputs used pandas float calculations and displayed Accessories profit
as 7402.82 and Notebook Pack profit as 1577.62. Exact CSV arithmetic under this
module's policy reports 7402.83 and 1577.63, respectively.

Margins remain unrounded ratios internally and are formatted to one decimal
percentage point with ROUND_HALF_UP. A zero-revenue margin is None.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = (
    "order_date",
    "product",
    "category",
    "region",
    "units_sold",
    "unit_price",
    "unit_cost",
    "discount_rate",
)
NUMERIC_COLUMNS = ("units_sold", "unit_price", "unit_cost", "discount_rate")
GROUP_DIMENSIONS = ("product", "category", "region", "month")
MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0")


class DataValidationError(ValueError):
    """Raised when input data is empty or violates the expected schema/rules."""


def round_currency(value: Decimal) -> Decimal:
    """Round a monetary amount to cents using the documented HALF_UP policy."""
    if not isinstance(value, Decimal):
        value = _parse_decimal(value, field="amount", row_number=None)
    if not value.is_finite():
        raise ValueError("Currency amounts must be finite decimals.")
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def format_percent(value: Decimal | None, decimal_places: int = 1) -> str:
    """Format an unrounded margin ratio as a percentage using HALF_UP."""
    if value is None:
        return "N/A"
    if not isinstance(value, Decimal):
        value = _parse_decimal(value, field="percentage", row_number=None)
    if not value.is_finite():
        raise ValueError("Percentage values must be finite decimals.")
    if not isinstance(decimal_places, int) or decimal_places < 0:
        raise ValueError("decimal_places must be a non-negative integer.")
    quantum = Decimal("1").scaleb(-decimal_places)
    percentage = (value * Decimal("100")).quantize(
        quantum, rounding=ROUND_HALF_UP
    )
    return f"{percentage:.{decimal_places}f}%"


def _parse_decimal(value: Any, *, field: str, row_number: int | None) -> Decimal:
    location = f" at data row {row_number}" if row_number is not None else ""
    if value is None or pd.isna(value) or str(value).strip() == "":
        raise DataValidationError(f"Missing numeric value for '{field}'{location}.")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DataValidationError(
            f"Invalid numeric value for '{field}'{location}: {value!r}."
        ) from exc
    if not parsed.is_finite():
        raise DataValidationError(f"Non-finite numeric value for '{field}'{location}.")
    return parsed


def _validate_and_normalize(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise DataValidationError("Input must be a pandas DataFrame.")
    if data.empty:
        raise DataValidationError("Input data is empty; expected at least one row.")

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise DataValidationError(f"Missing required columns: {', '.join(missing)}.")
    if data.columns.duplicated().any():
        raise DataValidationError("Input contains duplicate column names.")

    normalized = data.copy().reset_index(drop=True)
    for column in ("product", "category", "region"):
        values: list[str] = []
        for row_index, value in enumerate(normalized[column].tolist(), start=1):
            if value is None or pd.isna(value) or str(value).strip() == "":
                raise DataValidationError(
                    f"Missing value for '{column}' at data row {row_index}."
                )
            values.append(str(value).strip())
        normalized[column] = values

    parsed_dates = pd.to_datetime(normalized["order_date"], errors="coerce")
    invalid_dates = parsed_dates.isna()
    if invalid_dates.any():
        row_number = int(invalid_dates[invalid_dates].index[0]) + 1
        raise DataValidationError(
            f"Invalid or missing date in 'order_date' at data row {row_number}."
        )
    normalized["order_date"] = parsed_dates

    parsed_columns: dict[str, list[Decimal | int]] = {
        column: [] for column in NUMERIC_COLUMNS
    }
    for row_index, values in enumerate(
        normalized.loc[:, NUMERIC_COLUMNS].itertuples(index=False, name=None),
        start=1,
    ):
        parsed = {
            column: _parse_decimal(value, field=column, row_number=row_index)
            for column, value in zip(NUMERIC_COLUMNS, values)
        }
        units = parsed["units_sold"]
        if units < ZERO:
            raise DataValidationError(
                f"'units_sold' cannot be negative at data row {row_index}."
            )
        if units != units.to_integral_value():
            raise DataValidationError(
                f"'units_sold' must be a whole number at data row {row_index}."
            )
        for column in ("unit_price", "unit_cost"):
            if parsed[column] < ZERO:
                raise DataValidationError(
                    f"'{column}' cannot be negative at data row {row_index}."
                )
        discount = parsed["discount_rate"]
        if discount < ZERO or discount > Decimal("1"):
            raise DataValidationError(
                f"'discount_rate' must be between 0 and 1 at data row {row_index}."
            )
        parsed_columns["units_sold"].append(int(units))
        for column in ("unit_price", "unit_cost", "discount_rate"):
            parsed_columns[column].append(parsed[column])

    for column, values in parsed_columns.items():
        normalized[column] = pd.Series(values, index=normalized.index, dtype=object)
    return normalized


def calculate_metrics(data: pd.DataFrame) -> pd.DataFrame:
    """Validate raw sales records and return a copy with exact Decimal metrics.

    Derived columns are ``gross_sales``, ``revenue_after_discounts``,
    ``recorded_product_cost``, ``calculated_profit``, ``profit_margin`` and
    ``month``. No row-level monetary rounding is performed.
    """
    result = _validate_and_normalize(data)
    gross_sales: list[Decimal] = []
    revenue_after_discounts: list[Decimal] = []
    recorded_product_cost: list[Decimal] = []
    calculated_profit: list[Decimal] = []
    profit_margins: list[Decimal | None] = []
    months: list[str] = []

    for row in result.itertuples(index=False):
        units = Decimal(row.units_sold)
        gross = units * row.unit_price
        revenue = gross * (Decimal("1") - row.discount_rate)
        cost = units * row.unit_cost
        profit = revenue - cost
        gross_sales.append(gross)
        revenue_after_discounts.append(revenue)
        recorded_product_cost.append(cost)
        calculated_profit.append(profit)
        profit_margins.append(profit / revenue if revenue != ZERO else None)
        months.append(row.order_date.strftime("%Y-%m"))

    result["gross_sales"] = pd.Series(gross_sales, index=result.index, dtype=object)
    result["revenue_after_discounts"] = pd.Series(
        revenue_after_discounts, index=result.index, dtype=object
    )
    result["recorded_product_cost"] = pd.Series(
        recorded_product_cost, index=result.index, dtype=object
    )
    result["calculated_profit"] = pd.Series(
        calculated_profit, index=result.index, dtype=object
    )
    result["profit_margin"] = pd.Series(
        profit_margins, index=result.index, dtype=object
    )
    result["month"] = months
    return result


def load_sales_data(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Load and validate the project CSV, independent of the caller's cwd.

    When ``csv_path`` is omitted, the project's ``data/sales_data.csv`` is used.
    The returned frame includes the calculated metric columns.
    """
    path = (
        Path(csv_path).expanduser().resolve()
        if csv_path is not None
        else Path(__file__).resolve().parents[1] / "data" / "sales_data.csv"
    )
    try:
        raw_data = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError(f"CSV file is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise DataValidationError(f"Could not parse CSV file: {path}") from exc
    return calculate_metrics(raw_data)


def _safe_margin(profit: Decimal, revenue: Decimal) -> Decimal | None:
    return profit / revenue if revenue != ZERO else None


def summarize_metrics(data: pd.DataFrame) -> dict[str, int | Decimal | None]:
    """Return rounded overall monetary metrics and an unrounded margin ratio."""
    metrics = calculate_metrics(data)
    revenue = sum(metrics["revenue_after_discounts"], ZERO)
    cost = sum(metrics["recorded_product_cost"], ZERO)
    profit = sum(metrics["calculated_profit"], ZERO)
    units = sum(metrics["units_sold"], 0)
    return {
        "record_count": len(metrics),
        "units_sold": units,
        "revenue_after_discounts": round_currency(revenue),
        "recorded_product_cost": round_currency(cost),
        "calculated_profit": round_currency(profit),
        "profit_margin": _safe_margin(profit, revenue),
    }


def aggregate_metrics(data: pd.DataFrame, by: str) -> pd.DataFrame:
    """Aggregate metrics by product, category, region, or calendar month.

    Monetary totals are independently rounded to cents at the group reporting
    boundary. Consequently, displayed group totals may differ by a cent from a
    separately rounded grand total when fractional cents occur in multiple groups.
    """
    if by not in GROUP_DIMENSIONS:
        expected = ", ".join(GROUP_DIMENSIONS)
        raise ValueError(f"Unsupported grouping {by!r}; choose one of: {expected}.")

    metrics = calculate_metrics(data)
    grouped: dict[str, dict[str, Any]] = {}
    for row in metrics.itertuples(index=False):
        key = getattr(row, by)
        record = grouped.setdefault(
            key,
            {
                by: key,
                "record_count": 0,
                "units_sold": 0,
                "revenue_after_discounts": ZERO,
                "recorded_product_cost": ZERO,
                "calculated_profit": ZERO,
            },
        )
        record["record_count"] += 1
        record["units_sold"] += row.units_sold
        record["revenue_after_discounts"] += row.revenue_after_discounts
        record["recorded_product_cost"] += row.recorded_product_cost
        record["calculated_profit"] += row.calculated_profit

    records: list[dict[str, Any]] = []
    for record in grouped.values():
        exact_revenue = record["revenue_after_discounts"]
        exact_cost = record["recorded_product_cost"]
        exact_profit = record["calculated_profit"]
        records.append(
            {
                by: record[by],
                "record_count": record["record_count"],
                "units_sold": record["units_sold"],
                "revenue_after_discounts": round_currency(exact_revenue),
                "recorded_product_cost": round_currency(exact_cost),
                "calculated_profit": round_currency(exact_profit),
                "profit_margin": _safe_margin(exact_profit, exact_revenue),
            }
        )

    records.sort(key=lambda record: record["calculated_profit"], reverse=True)
    return pd.DataFrame(records)


def aggregate_monthly_metrics(data: pd.DataFrame) -> pd.DataFrame:
    """Return monthly metrics in chronological order for trend charts."""
    return aggregate_metrics(data, "month").sort_values("month", ignore_index=True)
