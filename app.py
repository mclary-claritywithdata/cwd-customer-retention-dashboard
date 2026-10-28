import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Who's Coming Back?",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Who’s Coming Back?")
st.caption(
    "A customer-retention snapshot: see who returns, who has gone quiet, "
    "and which products lead sales."
)

st.info(
    "Upload a transaction file with these columns: InvoiceNo, Description, "
    "Quantity, InvoiceDate, UnitPrice, and CustomerID. "
    "Sales values will use the currency in your file."
)
data_source = st.radio(
    "Choose your data",
    ["Try the demo data", "Upload your own file"],
    horizontal=True
)

ed_file = None

if data_source == "Upload your own file":
    st.subheader("Want help understanding your customer data?")
    st.write(
        "Clarity With Data can help your business turn transaction data "
        "into useful customer-retention insights."
    )
    st.info("Contact Clarity With Data to discuss becoming a customer.")
    st.stop()

if data_source == "Try the demo data":
    demo_path = Path(__file__).parent / "OnlineRetail.xlsx"
    try:
        df = pd.read_excel(demo_path)
    except Exception as error:
        st.error(f"Could not load the demo workbook: {error}")
        st.stop()

    st.caption(
        "Demo data: Chen, D. (2015). Online Retail. "
        "UCI Machine Learning Repository. "
        "https://doi.org/10.24432/C5BW33. Licensed under CC BY 4.0."
    )

elif uploaded_file is None:
    st.info("Upload a transaction file to explore your own data.")
    st.stop()

else:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as error:
        st.error(f"I couldn’t read that file: {error}")
        st.stop()
required_columns = [
    "InvoiceNo",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID"
]

missing_columns = [column for column in required_columns if column not in df.columns]

if missing_columns:
    st.error(
        "This file is missing required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()

# Prepare fields used in the analysis
df["InvoiceNo"] = df["InvoiceNo"].astype("string")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

# Keep identified customers' completed, positive-value purchases
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
    st.warning("No valid customer purchases were found in this file.")
    st.stop()

customer_sales["Sales"] = (
    customer_sales["Quantity"] * customer_sales["UnitPrice"]
)

# Summarize each identified customer
customer_summary = (
    customer_sales.groupby("CustomerID")
    .agg(
        orders=("InvoiceNo", "nunique"),
        total_spend=("Sales", "sum"),
        first_purchase=("InvoiceDate", "min"),
        last_purchase=("InvoiceDate", "max")
    )
    .reset_index()
)

# Use the latest transaction date in the file as the snapshot date
reference_date = customer_sales["InvoiceDate"].max()

customer_summary["days_since_last_order"] = (
    reference_date - customer_summary["last_purchase"]
).dt.days

customer_summary["segment"] = "One-time customer"

repeat_recent = (
    (customer_summary["orders"] >= 2)
    & (customer_summary["days_since_last_order"] <= inactive_days)
)

inactive_days = st.slider(
    "Consider a repeat customer inactive after this many days",
    min_value=30,
    max_value=180,
    value=90,
    step=15
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
    "Repeat customer, inactive"
]

segment_summary = (
    customer_summary.groupby("segment")
    .agg(
        customers=("CustomerID", "count"),
        avg_orders=("orders", "mean"),
        avg_spend=("total_spend", "mean")
    )
    .reindex(segment_order, fill_value=0)
    .reset_index()
)

segment_summary["percent_of_customers"] = (
    segment_summary["customers"]
    / len(customer_summary)
    * 100
).round(1)

repeat_count = int((customer_summary["orders"] >= 2).sum())
repeat_rate = repeat_count / len(customer_summary) * 100
inactive_repeat_count = int(repeat_inactive.sum())

# Key measures
col1, col2, col3, col4 = st.columns(4)

col1.metric("Identified customers", f"{len(customer_summary):,}")
col2.metric("Repeat customer rate", f"{repeat_rate:.1f}%")
col3.metric("Repeat customers inactive", f"{inactive_repeat_count:,}")
col4.metric("Products sold", f"{customer_sales['Description'].nunique():,}")

st.caption(
    f"Snapshot date: {reference_date:%b %d, %Y} "
    f" · Inactive cutoff: {inactive_days} days"
)

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Customers by segment")
    segment_chart = (
        segment_summary.set_index("segment")[["customers"]]
    )
    st.bar_chart(segment_chart)

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

# Segment details
st.subheader("Customer segment details")
st.dataframe(
    segment_summary.rename(
        columns={
            "segment": "Customer segment",
            "customers": "Customers",
            "avg_orders": "Average orders",
            "avg_spend": "Average spend",
            "percent_of_customers": "Share of customers (%)"
        }
    ).round(1),
    use_container_width=True,
    hide_index=True
)

# Allow a business to review and save the customer list
st.subheader("Customers to review")
inactive_customers = customer_summary.loc[
    customer_summary["segment"] == "Repeat customer, inactive"
].sort_values("days_since_last_order", ascending=False)

st.write(
    "These are identified repeat customers whose last order was more than "
    f"{inactive_days} days before the latest transaction date in the file."
)

st.dataframe(
    inactive_customers[
        [
            "CustomerID",
            "orders",
            "total_spend",
            "last_purchase",
            "days_since_last_order"
        ]
    ].rename(
        columns={
            "CustomerID": "Customer ID",
            "orders": "Orders",
            "total_spend": "Total spend",
            "last_purchase": "Last purchase",
            "days_since_last_order": "Days since last order"
        }
    ).round(2),
    use_container_width=True,
    hide_index=True
)

download_data = customer_summary.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download customer segments",
    data=download_data,
    file_name="customer_segments.csv",
    mime="text/csv"
)

st.caption(
    "This is a descriptive analysis, not a prediction of who will stop buying. "
    "Customers without an ID, cancellations, and non-positive purchases are "
    "excluded from customer-level results. Adjust the inactivity cutoff to "
    "match the business’s normal buying cycle."
)
