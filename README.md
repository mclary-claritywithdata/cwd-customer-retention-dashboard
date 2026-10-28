# Who’s Coming Back?

A Streamlit dashboard exploring repeat customer behavior, customer recency, and product sales.

## What it shows

- Customer segments: one-time, recent repeat, and inactive repeat
- Repeat-customer rate
- Top products by sales
- A review list of repeat customers who have not ordered within the selected inactivity window

The inactivity window is adjustable because a useful follow-up period depends on how often a business’s customers normally buy.

## Demo data and attribution

The dashboard includes the UCI Online Retail dataset as demo data, so visitors can explore it without uploading a file. The dataset covers 2010–2011 and reports sales in British pounds.

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. Licensed under CC BY 4.0.

Visitors can also upload their own CSV or Excel transaction file. Customer-level results exclude transactions without a customer ID, cancellations, duplicate rows, and non-positive quantities or prices. The inactive label is a rule-based signal for review, not a prediction of future behavior.

## Run the dashboard

Install the packages listed in `requirements.txt`, then run:

```bash
streamlit run app.py
