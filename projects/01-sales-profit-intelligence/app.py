"""Interactive Streamlit dashboard for the synthetic sales dataset."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sales_profit_metrics import (  # noqa: E402
    DataValidationError,
    aggregate_monthly_metrics,
    aggregate_metrics,
    format_percent,
    load_sales_data,
    round_currency,
    summarize_metrics,
)


st.set_page_config(
    page_title="Sales & Profit Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Loading and validating sales data…")
def get_sales_data() -> pd.DataFrame:
    """Load the project dataset through the validated metrics module."""
    return load_sales_data(PROJECT_ROOT / "data" / "sales_data.csv")


def money_label(value: Decimal) -> str:
    """Format dataset currency units without assuming a currency symbol."""
    return f"{round_currency(value):,.2f}"


def chart_frame(data: pd.DataFrame, *, dimension: str) -> pd.DataFrame:
    """Convert exact, presentation-rounded aggregates for Plotly rendering."""
    result = data.copy()
    for column in ("revenue_after_discounts", "recorded_product_cost", "calculated_profit"):
        result[column] = result[column].map(lambda value: float(round_currency(value)))
    if "profit_margin" in result.columns:
        result["profit_margin_percent"] = result["profit_margin"].map(
            lambda value: None if value is None else float(format_percent(value)[:-1])
        )
    return result


try:
    sales = get_sales_data()
except (DataValidationError, OSError, UnicodeError, pd.errors.ParserError) as exc:
    st.error(f"The sales dataset could not be loaded or validated: {exc}")
    st.info("Check that data/sales_data.csv exists and follows the documented schema.")
    st.stop()
except Exception as exc:  # Keep unexpected data-loading errors visible and actionable.
    st.error(f"Unexpected error while loading the sales dataset: {exc}")
    st.stop()


st.title("Sales & Profit Intelligence")
st.caption("Interactive Descriptive Analysis of Synthetic Sales Data")
st.info(
    "**Synthetic dataset:** these records are for portfolio demonstration only. "
    "Calculated profit is revenue after discounts minus recorded product cost; "
    "it excludes operating expenses, taxes, and other business costs, so it is "
    "not net profit or a complete measure of business profitability."
)


with st.sidebar:
    st.header("Filters")
    minimum_date = sales["order_date"].min().date()
    maximum_date = sales["order_date"].max().date()
    selected_dates = st.date_input(
        "Order date range",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    def dimension_filter(label: str, column: str) -> list[str]:
        options = sorted(sales[column].unique().tolist())
        return st.multiselect(label, options, default=options)

    selected_categories = dimension_filter("Category", "category")
    selected_regions = dimension_filter("Region", "region")
    selected_products = dimension_filter("Product", "product")


if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
elif isinstance(selected_dates, date):
    start_date = end_date = selected_dates
else:
    start_date, end_date = minimum_date, maximum_date

filtered = sales.loc[
    sales["order_date"].dt.date.between(start_date, end_date)
    & sales["category"].isin(selected_categories)
    & sales["region"].isin(selected_regions)
    & sales["product"].isin(selected_products)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters. Adjust the filters to continue.")
    st.stop()

summary = summarize_metrics(filtered)
metric_columns = st.columns(5)
metric_columns[0].metric(
    "Revenue After Discounts",
    money_label(summary["revenue_after_discounts"]),
    help="Revenue after discounts, in dataset currency units.",
)
metric_columns[1].metric("Recorded Product Cost", money_label(summary["recorded_product_cost"]))
metric_columns[2].metric("Calculated Profit", money_label(summary["calculated_profit"]))
metric_columns[3].metric("Profit Margin", format_percent(summary["profit_margin"]))
metric_columns[4].metric("Units Sold", f"{summary['units_sold']:,}")
st.caption(f"Dataset currency units | {summary['record_count']:,} sales records in the current selection")


monthly = chart_frame(aggregate_monthly_metrics(filtered), dimension="month")
monthly_periods = [pd.Period(month, freq="M") for month in monthly["month"]]
monthly_years = sorted({period.year for period in monthly_periods})
product = chart_frame(aggregate_metrics(filtered, "product"), dimension="product")
category = chart_frame(aggregate_metrics(filtered, "category"), dimension="category")
region = chart_frame(aggregate_metrics(filtered, "region"), dimension="region")

left, right = st.columns(2)
with left:
    st.subheader("Monthly Revenue and Calculated Profit")
    trend = go.Figure()
    trend.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["revenue_after_discounts"],
        mode="lines+markers", name="Revenue After Discounts",
        hovertemplate="%{x}<br>Revenue After Discounts: %{y:,.2f}<extra></extra>",
    ))
    trend.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["calculated_profit"],
        mode="lines+markers", name="Calculated Profit",
        hovertemplate="%{x}<br>Calculated Profit: %{y:,.2f}<extra></extra>",
    ))
    trend.update_layout(
        xaxis_title=f"Month ({monthly_years[0]})" if len(monthly_years) == 1 else "Month",
        yaxis_title="Dataset currency units",
        hovermode="x unified", legend_title_text="Metric", margin=dict(t=20, b=20),
    )
    first_month = monthly_periods[0]
    last_month = monthly_periods[-1]
    trend.update_xaxes(
        range=[
            (first_month.start_time - pd.Timedelta(days=5)).isoformat(),
            (last_month.end_time - pd.Timedelta(days=5)).isoformat(),
        ],
        tickmode="array",
        tickvals=monthly["month"].tolist(),
        ticktext=[period.strftime("%b") for period in monthly_periods],
    )
    st.plotly_chart(trend, width="stretch")

with right:
    st.subheader("Calculated Profit by Product")
    product_chart = px.bar(
        product.sort_values("calculated_profit"),
        x="calculated_profit", y="product", orientation="h",
        labels={
            "calculated_profit": "Calculated Profit",
            "product": "Product",
            "revenue_after_discounts": "Revenue After Discounts",
            "profit_margin_percent": "Profit Margin",
        },
        hover_data={"revenue_after_discounts": ":,.2f", "profit_margin_percent": ":.1f"},
        color="calculated_profit", color_continuous_scale="Teal",
    )
    product_chart.update_layout(
        coloraxis_showscale=False, xaxis_title="Dataset currency units",
        yaxis_title="", margin=dict(t=20, b=20),
    )
    st.plotly_chart(product_chart, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Category Performance")
    category_long = category.melt(
        id_vars="category",
        value_vars=["revenue_after_discounts", "calculated_profit"],
        var_name="Metric", value_name="Dataset currency units",
    )
    category_long["Metric"] = category_long["Metric"].map({
        "revenue_after_discounts": "Revenue After Discounts",
        "calculated_profit": "Calculated Profit",
    })
    category_chart = px.bar(
        category_long, x="category", y="Dataset currency units", color="Metric",
        barmode="group", labels={"category": "Category"},
        color_discrete_sequence=["#0F766E", "#F59E0B"],
        hover_data={"Dataset currency units": ":,.2f"},
    )
    category_chart.update_layout(margin=dict(t=20, b=20), legend_title_text="")
    st.plotly_chart(category_chart, width="stretch")

with right:
    st.subheader("Regional Performance")
    region_long = region.melt(
        id_vars="region",
        value_vars=["revenue_after_discounts", "calculated_profit"],
        var_name="Metric", value_name="Dataset currency units",
    )
    region_long["Metric"] = region_long["Metric"].map({
        "revenue_after_discounts": "Revenue After Discounts",
        "calculated_profit": "Calculated Profit",
    })
    region_chart = px.bar(
        region_long, x="region", y="Dataset currency units", color="Metric",
        barmode="group", labels={"region": "Region"},
        color_discrete_sequence=["#0F766E", "#F59E0B"],
        hover_data={"Dataset currency units": ":,.2f"},
    )
    region_chart.update_layout(margin=dict(t=20, b=20), legend_title_text="")
    st.plotly_chart(region_chart, width="stretch")


st.subheader("Business Highlights")
category_leader = category.sort_values("calculated_profit", ascending=False).iloc[0]
product_profit_leader = product.sort_values("calculated_profit", ascending=False).iloc[0]
product_margin_leader = product.sort_values("profit_margin", ascending=False).iloc[0]
region_leader = region.sort_values("calculated_profit", ascending=False).iloc[0]
highlight_columns = st.columns(4)
highlight_columns[0].metric(
    "Top Category by Calculated Profit",
    str(category_leader["category"]),
    help="Category with the highest calculated profit in the current filtered selection.",
)
highlight_columns[1].metric(
    "Top Product by Calculated Profit",
    str(product_profit_leader["product"]),
    help="Product with the highest calculated profit in the current filtered selection.",
)
highlight_columns[2].metric(
    "Highest-Margin Product",
    str(product_margin_leader["product"]),
    format_percent(product_margin_leader["profit_margin"]),
    help="Highest calculated profit margin among products in the current filtered selection.",
)
highlight_columns[3].metric(
    "Top Region by Calculated Profit",
    str(region_leader["region"]),
    help="Region with the highest calculated profit in the current filtered selection.",
)
st.caption(
    "Highlights update with the selected filters. They describe this synthetic dataset and "
    "should be treated as descriptive signals, not causal explanations or real-business claims."
)

with st.expander("Metric Definitions and Methodology"):
    st.markdown(
        "- **Revenue After Discounts** = units sold × unit price × (1 − discount rate)\n"
        "- **Recorded Product Cost** = units sold × unit cost\n"
        "- **Calculated Profit** = Revenue After Discounts − Recorded Product Cost\n"
        "- **Profit Margin** = Calculated Profit ÷ Revenue After Discounts\n\n"
        "The shared metrics module aggregates exact decimal values without row-level rounding. "
        "Displayed monetary amounts use `ROUND_HALF_UP` to two decimal places; margins use "
        "unrounded aggregate values and are formatted to one decimal place."
    )
