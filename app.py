from pathlib import Path

import pandas as pd
import streamlit as st


# -----------------------------------------------------------------------------
# Page setup and CWD branding
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Comeback | Clarity With Data",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        .cwd-brand {
            color: #55c7b4;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            margin-bottom: 0.25rem;
        }
        .cwd-subtitle {font-size: 1.05rem; opacity: 0.84;}
        div[data-testid="stMetric"] {
            background: rgba(85, 199, 180, 0.08);
            border: 1px solid rgba(85, 199, 180, 0.25);
            padding: 1rem;
            border-radius: 0.75rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="cwd-brand">CLARITY WITH DATA</div>', unsafe_allow_html=True)
st.title("📊 Customer Comeback")
st.markdown(
    '<div class="cwd-subtitle">A clear snapshot of who returns, what they buy, '
    'and where to focus next.</div>',
    unsafe_allow_html=True,
)
st.write("")

# -----------------------------------------------------------------------------
# Data choice
# -----------------------------------------------------------------------------
st.info(
    "This dashboard uses sample transaction data. Interested in insights from your own data? Select"
    "Upload your own file to learn how Clarity With Data can help."
)

data_source = st.radio(
    "Choose your data",
    ["Try the demo data", "Upload your own file"],
    horizontal=True,
)

if data_source == "Upload your own file":
    st.subheader("Bring your customer data into focus")
    st.write(
        "Turn your data it into clear, useful customer-retention insights."
         "Interested in working together? Contact Clarity With Data to discuss a customer analysis for your organization."
        "https://www.claritywithdata.com/contact"
    )
    st.info("Contact Clarity With Data to discuss becoming a customer.")
    st.stop()

# The demo workbook is stored in the repository next to this app.py file.
demo_path = Path(__file__).parent / "OnlineRetail.xlsx"
try:
    df = pd.read_excel(demo_path)
except FileNotFoundError:
    st.error(
        "The demo workbook (OnlineRetail.xlsx) is missing from the app repository. "
        "Please add it next to app.py and redeploy."
    )
    st.stop()
except Exception as error:
    st.error(f"Could not load the demo workbook: {error}")
    st.stop()

st.caption(
    "Demo data: Chen, D. (2015). Online Retail. UCI Machine Learning Repository. "
    "https://doi.org/10.24432/C5BW33. Licensed under CC BY 4.0."
)

# -----------------------------------------------------------------------------
# Validate and prepare data
# -----------------------------------------------------------------------------
required_columns = [
    "InvoiceNo",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
]
missing_columns = [column for column in required_columns if column not in df.columns]
if missing_columns:
    st.error("The demo file is missing required columns: " + ", ".join(missing_columns))
    st.stop()

df = df.copy()
df["InvoiceNo"] = df["InvoiceNo"].astype("string")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

valid_purchases = (
    df["CustomerID"].notna()
    & df["InvoiceNo"].notna()
    & ~df["InvoiceNo"].str.startswith("C", na=False)
    & (df["Quantity"] > 0)
    & (df["UnitPrice"] > 0)
    & df["InvoiceDate"].notna()
)
customer_sales = df.loc[valid_purchases].drop_duplicates().copy()
if customer_sales.empty:
    st.warning("No valid customer purchases were found in the demo file.")
    st.stop()

customer_sales["Sales"] = customer_sales["Quantity"] * customer_sales["UnitPrice"]

customer_summary = (
    customer_sales.groupby("CustomerID")
    .agg(
        orders=("InvoiceNo", "nunique"),
        total_spend=("Sales", "sum"),
        first_purchase=("InvoiceDate", "min"),
        last_purchase=("InvoiceDate", "max"),
    )
    .reset_index()
)

reference_date = customer_sales["InvoiceDate"].max()
customer_summary["days_since_last_order"] = (
    reference_date - customer_summary["last_purchase"]
).dt.days
customer_summary["segment"] = "One-time customer"

# Define the cutoff before using it in the segment masks.
inactive_days = st.slider(
    "Consider a repeat customer inactive after this many days",
    min_value=30,
    max_value=180,
    value=90,
    step=15,
)

repeat_recent = (
    (customer_summary["orders"] >= 2)
    & (customer_summary["days_since_last_order"] <= inactive_days)
)
repeat_inactive = (
    (customer_summary["orders"] >= 2)
    & (customer_summary["days_since_last_order"] > inactive_days)
)
customer_summary.loc[repeat_recent, "segment"] = "Repeat customer, recent"
customer_summary.loc[repeat_inactive, "segment"] = "Repeat customer, inactive"

segment_order = [
    "One-time customer",
    "Repeat customer, recent",
    "Repeat customer, inactive",
]
segment_summary = (
    customer_summary.groupby("segment")
    .agg(
        customers=("CustomerID", "count"),
        avg_orders=("orders", "mean"),
        avg_spend=("total_spend", "mean"),
    )
    .reindex(segment_order, fill_value=0)
    .reset_index()
)
segment_summary["percent_of_customers"] = (
    segment_summary["customers"] / len(customer_summary) * 100
).round(1)

repeat_count = int((customer_summary["orders"] >= 2).sum())
repeat_rate = repeat_count / len(customer_summary) * 100
inactive_repeat_count = int(repeat_inactive.sum())

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Identified customers", f"{len(customer_summary):,}")
col2.metric("Repeat customer rate", f"{repeat_rate:.1f}%")
col3.metric("Repeat customers inactive", f"{inactive_repeat_count:,}")
col4.metric("Products sold", f"{customer_sales['Description'].nunique():,}")

st.caption(
    f"Snapshot date: {reference_date:%b %d, %Y}  ·  "
    f"Inactive cutoff: {inactive_days} days  ·  Demo sales currency: GBP (£)"
)

left, right = st.columns(2)
with left:
    st.subheader("Customers by segment")
    st.bar_chart(segment_summary.set_index("segment")[["customers"]])

with right:
    st.subheader("Top 10 products by sales")
    top_products = (
        customer_sales.dropna(subset=["Description"])
        .groupby("Description")["Sales"]
        .sum()
        .nlargest(10)
        .sort_values()
    )
    st.bar_chart(top_products)

st.subheader("Customer segment details")
st.dataframe(
    segment_summary.rename(
        columns={
            "segment": "Customer segment",
            "customers": "Customers",
            "avg_orders": "Average orders",
            "avg_spend": "Average spend (£)",
            "percent_of_customers": "Share of customers (%)",
        }
    ).round(1),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Repeat customers to review")
inactive_customers = customer_summary.loc[
    customer_summary["segment"] == "Repeat customer, inactive"
].sort_values("days_since_last_order", ascending=False)
st.write(
    "These repeat customers last ordered more than "
    f"{inactive_days} days before the latest transaction date in the file."
)
st.dataframe(
    inactive_customers[
        ["CustomerID", "orders", "total_spend", "last_purchase", "days_since_last_order"]
    ].rename(
        columns={
            "CustomerID": "Customer ID",
            "orders": "Orders",
            "total_spend": "Total spend (£)",
            "last_purchase": "Last purchase",
            "days_since_last_order": "Days since last order",
        }
    ).round(2),
    use_container_width=True,
    hide_index=True,
)

download_data = customer_summary.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download customer segments",
    data=download_data,
    file_name="customer_segments.csv",
    mime="text/csv",
)

st.caption(
    "This is descriptive analysis, not a prediction of who will stop buying. "
    "Customers without an ID, cancellations, and non-positive purchases are "
    "excluded from customer-level results. Set the inactivity cutoff to match "
    "the business’s normal buying cycle."
)
