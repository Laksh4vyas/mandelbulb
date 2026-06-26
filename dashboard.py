import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px


# PAGE CONFIG


st.set_page_config(
    page_title="RetailMart Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)


# SIDEBAR


st.sidebar.title("⚙ Dashboard Settings")

dark_mode = st.sidebar.toggle(
    "🌙 Dark Mode",
    value=False
)

template = "plotly_dark" if dark_mode else "plotly_white"


# CUSTOM CSS


st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

h1 {
    color: #2563eb;
}

[data-testid="metric-container"] {
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
}

</style>
""", unsafe_allow_html=True)


# TITLE


st.title("📊 RetailMart Analytics Dashboard")

st.caption(
    "Built with Python • Pandas • NumPy • SQLite • Streamlit • Plotly"
)

st.divider()


# DATABASE CONNECTION


try:

    engine = create_engine(
        "sqlite:///database/retail.db"
    )

    df = pd.read_sql(
        "SELECT * FROM retail_sales",
        engine
    )

except Exception as e:

    st.error(
        f"Database Error: {e}"
    )

    st.stop()


# DATA PREPARATION


df["sale_date"] = pd.to_datetime(df["sale_date"])


# FILTERS


st.sidebar.header("🔎 Filters")

selected_city = st.sidebar.selectbox(
    "Filter by City",
    ["All"] + sorted(df["city"].unique().tolist())
)

if selected_city != "All":

    filtered_df = df[
        df["city"] == selected_city
    ]

else:

    filtered_df = df.copy()


# KPI SECTION


total_transactions = len(filtered_df)

total_revenue = filtered_df[
    "total_revenue"
].sum()

total_cities = filtered_df[
    "city"
].nunique()

total_products = filtered_df[
    "product_name"
].nunique()

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "💳 Transactions",
        f"{total_transactions:,}"
    )

with col2:

    st.metric(
        "💰 Revenue",
        f"₹{total_revenue:,.0f}"
    )

with col3:

    st.metric(
        "🏙 Cities",
        total_cities
    )

with col4:

    st.metric(
        "📦 Products",
        total_products
    )

st.divider()


# REVENUE BY CITY


col1, col2 = st.columns(2)

with col1:

    st.subheader("🏙 Revenue by City")

    city_revenue = (
        filtered_df.groupby("city")["total_revenue"]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        city_revenue,
        x="city",
        y="total_revenue",
        title="Revenue by City",
        template=template
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

with col2:

    st.subheader("🌎 Revenue Distribution")

    region_revenue = (
        filtered_df.groupby("region")["total_revenue"]
        .sum()
        .reset_index()
    )

    fig = px.pie(
        region_revenue,
        names="region",
        values="total_revenue",
        title="Revenue by Region",
        template=template
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )


# PRODUCT PERFORMANCE


col1, col2 = st.columns(2)

with col1:

    st.subheader("🔥 Best Selling Products")

    product_sales = (
        filtered_df.groupby("product_name")["quantity"]
        .sum()
        .reset_index()
        .sort_values(
            by="quantity",
            ascending=False
        )
    )

    fig = px.bar(
        product_sales,
        x="product_name",
        y="quantity",
        title="Best Selling Products",
        template=template
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

with col2:

    st.subheader("📈 Daily Revenue Trend")

    daily_revenue = (
        filtered_df.groupby("sale_date")["total_revenue"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        daily_revenue,
        x="sale_date",
        y="total_revenue",
        title="Daily Revenue Trend",
        markers=True,
        template=template
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

st.divider()


# TOP PRODUCTS TABLE


st.subheader("🏆 Top Products")

top_products = (
    filtered_df.groupby("product_name")["quantity"]
    .sum()
    .reset_index()
    .sort_values(
        by="quantity",
        ascending=False
    )
)

st.dataframe(
    top_products,
    width="stretch"
)


# BUSINESS INSIGHTS


st.subheader("💡 Business Insights")

best_city = (
    filtered_df.groupby("city")["total_revenue"]
    .sum()
    .idxmax()
)

best_product = (
    filtered_df.groupby("product_name")["quantity"]
    .sum()
    .idxmax()
)

highest_transaction = (
    filtered_df["total_revenue"]
    .max()
)

avg_revenue = (
    filtered_df["total_revenue"]
    .mean()
)

st.success(
    f"""
📍 Top Revenue City: **{best_city}**

🛒 Best Selling Product: **{best_product}**

💰 Highest Transaction Revenue: **₹{highest_transaction:,.0f}**

📊 Average Transaction Revenue: **₹{avg_revenue:,.0f}**
"""
)


# DATASET SUMMARY


st.subheader("📋 Dataset Summary")

summary_df = pd.DataFrame({
    "Metric": [
        "Transactions",
        "Revenue",
        "Cities",
        "Products"
    ],
    "Value": [
        total_transactions,
        round(total_revenue, 2),
        total_cities,
        total_products
    ]
})

st.dataframe(
    summary_df,
    width="stretch"
)


# DOWNLOAD BUTTON


st.subheader("⬇ Export Dataset")

csv = filtered_df.to_csv(
    index=False
)

st.download_button(
    label="Download CSV",
    data=csv,
    file_name="retail_sales.csv",
    mime="text/csv"
)


# RAW DATA


with st.expander("📄 View Full Dataset"):

    st.dataframe(
        filtered_df,
        width="stretch"
    )


# FOOTER


st.divider()

st.caption(
    "RetailMart Data Engineering Project | Python • Pandas • NumPy • SQLite • Streamlit • Plotly"
)