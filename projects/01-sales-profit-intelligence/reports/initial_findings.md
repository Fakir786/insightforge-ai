# Sales & Profit Intelligence — Findings Report

**Project type:** Portfolio case study  
**Data source:** Synthetic sales dataset created for demonstration  
**Records analyzed:** 49  
**Currency:** Not specified; all monetary figures are dataset currency units

## Executive Summary

The dataset contains 49 sales records and 890 units sold. Revenue after discounts totals **39,074.47**, recorded product cost totals **22,642.90**, and calculated profit totals **16,431.57**. The overall calculated profit margin is **42.1%**.

These figures describe only the synthetic dataset. They are not evidence of the performance of a real company.

## Key Findings

| Area | Finding | Interpretation |
|---|---|---|
| Overall | 39,074.47 revenue after discounts; 16,431.57 calculated profit | Calculated profit is revenue after discounts less recorded product cost. |
| Category | Accessories leads calculated profit at 7,402.83, with a 50.3% margin | This category contributes the most calculated profit in the sample. |
| Region | North leads regional calculated profit at 4,560.56 | North is the top region by total calculated profit, not necessarily by margin or growth. |
| Product | Monitor 24in leads product calculated profit at 3,509.75, with a 29.6% margin | It contributes the most calculated profit among products in this dataset. |
| Product margin | Notebook Pack has a 63.0% margin and 1,577.63 calculated profit | The highest margin does not automatically mean the highest total profit. |

## Recommended Business Questions

1. **Product mix:** What explains the difference between the product with the highest total calculated profit and the product with the highest margin?
2. **Regional performance:** Do regional differences remain after comparing sales volume, product mix, and margin?
3. **Discounts:** How are discount rates associated with revenue and calculated profit across products?
4. **Monthly trend:** Which months show unusually high or low revenue or calculated profit, and what additional data would help explain those changes?

These are investigation questions, not proven explanations. The dataset is small and synthetic, so no causal claims should be made.

## Metric Definitions

- **Revenue after discounts** = units sold × unit price × (1 − discount rate)
- **Recorded product cost** = units sold × unit cost
- **Calculated profit** = revenue after discounts − recorded product cost
- **Calculated profit margin** = calculated profit ÷ revenue after discounts

The reported profit is **not net profit**: operating expenses, taxes, and other business costs are not included. The dataset does not specify a currency.

## Data Quality and Method

The project validates required columns, dates, text dimensions, numeric values, and discount-rate bounds before calculating metrics. Monetary calculations retain decimal precision through aggregation, then reported amounts are rounded to two decimal places using ROUND_HALF_UP.

The saved executed notebook currently contains historical outputs from an earlier calculation version. Regenerate and review those outputs before treating the notebook as the canonical numerical record. The source notebook is maintained separately from the executed report.

## Limitations

- Synthetic data; no real company, customer, or market is represented.
- Only 49 records; findings are illustrative and not statistically generalizable.
- Currency is unspecified.
- Calculated profit excludes operating expenses, taxes, and other business costs.
- Descriptive comparisons do not establish causation.
- Discount impact has not yet been quantified.

## Next Steps

1. Re-run the source notebook in a controlled environment and verify all outputs against the current metrics module.
2. Add automated checks for dashboard filter combinations and empty selections.
3. Add a documented SQL analysis layer and compare selected SQL aggregates with the Python results.
4. Export clean, current chart images for the README and portfolio presentation.
