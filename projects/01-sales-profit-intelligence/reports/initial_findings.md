# Sales & Profit Intelligence — Findings Report

**Dataset:** Synthetic sales demonstration data  
**Reporting period:** January–December 2025  
**Records analyzed:** 49  
**Status:** Completed descriptive analysis

## Executive summary

This case study analyzes a small synthetic sales dataset to demonstrate data validation, business metric calculation, grouped performance analysis, and dashboard reporting. The records contain 890 units sold and 39,074.47 in revenue after discounts. After subtracting 22,642.90 in recorded product cost, calculated profit is 16,431.57, giving an aggregate profit margin of 42.1%.

These figures describe only the supplied demonstration dataset. They are not actual company results and should not be used as evidence of commercial performance.

## Method and metric definitions

- **Gross sales** = units sold × unit price
- **Revenue after discounts** = gross sales × (1 − discount rate)
- **Recorded product cost** = units sold × unit cost
- **Calculated profit** = revenue after discounts − recorded product cost
- **Profit margin** = calculated profit ÷ revenue after discounts

Monetary calculations use decimal values from the CSV without rounding individual records. Aggregated monetary values are rounded to two decimal places using `ROUND_HALF_UP`. Overall and group margins use aggregate profit divided by aggregate revenue.

## Data quality and scope

- 49 sales records and 8 required columns were analyzed.
- The dataset contains 890 units sold.
- The source dataset is synthetic and does not represent a real company, customer, or market.
- No currency is specified; amounts are therefore reported in dataset currency units.
- Calculated profit subtracts recorded product cost only. Operating expenses, taxes, and other business costs are excluded, so this is not net profit.
- The analysis is descriptive and does not establish causation.

## Overall results

| Measure | Result |
|---|---:|
| Sales records | 49 |
| Units sold | 890 |
| Revenue after discounts | 39,074.47 |
| Recorded product cost | 22,642.90 |
| Calculated profit | 16,431.57 |
| Aggregate profit margin | 42.1% |

## Findings by business question

### 1. Which products generate the most calculated profit?

| Product | Revenue after discounts | Calculated profit | Profit margin |
|---|---:|---:|---:|
| Monitor 24in | 11,858.75 | 3,509.75 | 29.6% |
| USB-C Hub | 5,242.69 | 2,677.69 | 51.1% |
| Office Chair | 7,278.65 | 2,586.65 | 35.5% |
| Wireless Mouse | 4,358.26 | 2,468.26 | 56.6% |
| Mechanical Keyboard | 5,112.88 | 2,256.88 | 44.1% |
| Notebook Pack | 2,504.53 | 1,577.63 | 63.0% |
| Desk Lamp | 2,718.72 | 1,354.72 | 49.8% |

**Finding:** Monitor 24in has the highest total calculated profit (3,509.75), but also the lowest product margin (29.6%). Notebook Pack has the highest product margin (63.0%) but lower total calculated profit (1,577.63). This illustrates the difference between profit contribution and margin.

### 2. Which categories contribute most to calculated profit?

| Category | Revenue after discounts | Calculated profit | Profit margin |
|---|---:|---:|---:|
| Accessories | 14,713.83 | 7,402.83 | 50.3% |
| Furniture | 9,997.37 | 3,941.37 | 39.4% |
| Electronics | 11,858.75 | 3,509.75 | 29.6% |
| Stationery | 2,504.53 | 1,577.63 | 63.0% |

**Finding:** Accessories contributes the highest calculated profit (7,402.83). Stationery has the highest category margin (63.0%), while contributing less total profit because its revenue base is smaller.

### 3. How do regions compare?

| Region | Revenue after discounts | Calculated profit | Profit margin |
|---|---:|---:|---:|
| North | 10,909.36 | 4,560.56 | 41.8% |
| South | 9,837.13 | 4,264.63 | 43.4% |
| East | 10,050.64 | 3,997.14 | 39.8% |
| West | 8,277.34 | 3,609.24 | 43.6% |

**Finding:** North has the highest calculated profit (4,560.56). West has the highest regional margin (43.6%), narrowly ahead of South (43.4%). Differences in product mix and sales volume may contribute to these results, but this dataset does not establish the causes.

### 4. What happened across the months?

- **December 2025** recorded the highest monthly revenue (6,733.91) and calculated profit (2,705.91).
- **February 2025** recorded the lowest monthly calculated profit (783.11).
- **April 2025** recorded the highest monthly profit margin (47.6%).

The monthly results are descriptive. The available records do not explain why performance differs between months.

### 5. What is the relationship between discounts and profitability?

A discount-impact analysis has not been performed in this report. The current results do not establish whether discounts increase or reduce profit. A separate analysis would need to compare discount rates with revenue, calculated profit, and margin while accounting for product and sales mix. Any observed relationship should be described as an association, not a causal effect.

## Business interpretation and follow-up work

The dataset demonstrates why decision-makers should review total profit and profit margin together:

- Review the cost and pricing structure of Monitor 24in because it contributes the highest total profit but has the lowest product margin in this sample.
- Examine whether Notebook Pack's high margin can be sustained at its observed sales volume.
- Investigate the product mix behind regional differences before attributing performance to a region itself.
- Explore monthly changes with additional context before proposing operational explanations.
- Conduct a separate discount analysis before making discount-policy recommendations.

These are investigation priorities for the demonstration dataset, not operational recommendations for a real business.

## Reproducibility

The analysis can be reproduced from the project source:

1. Install dependencies listed in `requirements.txt`.
2. Run `notebooks/sales_profit_analysis.ipynb` from the documented project setup.
3. Run the automated metric tests with:

```powershell
python -B -m unittest discover -s tests -v
```

The reusable calculations are implemented in `src/sales_profit_metrics.py`. The interactive dashboards are documented in the project README.

## Limitations

- The dataset is synthetic and contains only 49 records.
- The dataset does not identify a currency.
- Calculated profit excludes operating expenses, taxes, and other business costs; it is not net profit.
- The analysis is descriptive and does not establish causation.
- Discount impact has not been quantified.
- Results should not be represented as actual company or customer performance.
