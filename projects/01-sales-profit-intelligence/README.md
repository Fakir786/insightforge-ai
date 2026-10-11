# Sales & Profit Intelligence

**Portfolio project | Data Analytics | Python, Pandas, Matplotlib**

## Business question

Which products, categories, regions, and months contribute most to sales and profit, and where should a business investigate opportunities to improve performance?

## Project goals

- Inspect and validate a sales dataset.
- Calculate revenue, cost, profit, and profit margin.
- Compare performance by product, category, region, and month.
- Communicate findings with clear visualizations.
- Turn the analysis into practical, evidence-based business recommendations.

## Dataset

The file `data/sales_data.csv` contains **synthetic demonstration data created for this portfolio**. It does not represent a real company or actual customer transactions. The dataset includes order dates, products, categories, regions, units sold, unit prices, unit costs, and discount rates.

## Tools

- Python
- Pandas
- Matplotlib
- Jupyter Notebook

## Project structure

```text
01-sales-profit-intelligence/
├── README.md
├── data/
│   └── sales_data.csv
├── notebooks/
│   └── sales_profit_analysis.ipynb
├── reports/
│   └── initial_findings.md
└── requirements.txt
```

## How to run

From this project directory:

1. Create and activate a Python virtual environment (recommended).
2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Start Jupyter:

   ```bash
   jupyter notebook notebooks/sales_profit_analysis.ipynb
   ```

4. Run the notebook cells from top to bottom.

The notebook reads the CSV using a relative path, so the project can be cloned to another computer.

## Key metrics

- **Gross sales before discount** = units sold × unit price
- **Revenue after discount** = gross sales × (1 − discount rate)
- **Cost** = units sold × unit cost
- **Profit** = revenue after discount − cost
- **Profit margin** = profit ÷ revenue after discount

The margin is shown as a percentage and is not the same as a markup on cost.

## Quality and limitations

- The dataset is synthetic and designed for learning and demonstration.
- The analysis does not claim to measure the performance of a real business.
- The findings report should be updated after running the notebook; conclusions must be supported by calculated results rather than assumed in advance.
- This is a portfolio case study, not financial or investment advice.

## Next improvements

- Add automated data-quality checks and tests.
- Add SQL queries for the same business questions.
- Build a Power BI dashboard from the cleaned dataset.
- Add screenshots of the completed dashboard and a concise executive summary.

---

*Created as a data analytics portfolio case study.*
