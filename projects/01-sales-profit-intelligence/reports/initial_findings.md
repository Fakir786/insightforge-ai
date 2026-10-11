# Initial Findings Report

**Project:** Sales & Profit Intelligence  
**Dataset:** Synthetic demonstration data created for this portfolio  
**Status:** Initial report template — run the notebook before publishing numerical findings

## Executive summary

This case study demonstrates how an analyst can turn transactional sales data into revenue, cost, profit, and profit-margin metrics. The dataset is synthetic; therefore, the analysis is a demonstration of methods and should not be presented as evidence about a real business.

## Questions addressed

1. Which products generate the most total profit?
2. Which categories and regions contribute most to profit?
3. How do revenue and profit change month by month?
4. How might discounts relate to profitability?

## Metrics

- **Revenue:** units sold × unit price × (1 − discount rate)
- **Cost:** units sold × unit cost
- **Profit:** revenue − cost
- **Profit margin:** profit ÷ revenue

## Results

Run `notebooks/sales_profit_analysis.ipynb` from top to bottom and use its tables and charts to fill in this section. Do not copy in estimated or invented figures.

| Question | Evidence to record | Business interpretation |
|---|---|---|
| Most profitable product | Product name and calculated profit | Check whether profit is driven by volume, price, or cost |
| Most profitable category | Category and calculated profit | Compare category contribution and margin |
| Regional performance | Revenue, profit, and margin by region | Identify areas for further investigation |
| Monthly trend | Monthly revenue and profit chart | Investigate unusual changes before drawing conclusions |
| Discount impact | Compare discount levels and profit margin | Treat this as an association, not proof of causation |

## Recommendations framework

After reviewing the actual notebook output, recommendations may include:
- Investigating products with high sales but weak margins.
- Reviewing pricing and discount rules where profitability is lower.
- Comparing regional results while accounting for product mix.
- Monitoring monthly indicators using a repeatable dashboard.

Only include a recommendation if the calculated results support it. State assumptions and limitations.

## Limitations

- The records are synthetic and are not representative of a real business.
- The sample is small and designed for portfolio demonstration.
- No causal relationship can be established from these records.
- No currency is specified; amounts are described as dataset currency units.

## Reproducibility

Install dependencies with `python -m pip install -r requirements.txt`, then run the notebook. Update this report only after checking the resulting tables and charts.
