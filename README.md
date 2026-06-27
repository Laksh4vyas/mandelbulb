# 🚀 Retail Data Engineering & Analytics Platform

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge\&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Engineering-black?style=for-the-badge\&logo=pandas)
![SQLite](https://img.shields.io/badge/SQLite-Warehouse-blue?style=for-the-badge\&logo=sqlite)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?style=for-the-badge\&logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-purple?style=for-the-badge\&logo=plotly)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=for-the-badge\&logo=docker)

</p>

---

# 🌐 LIVE APPLICATION

# **👉 https://mandelbulb-4omxqtuh369sbcxvj37rtn.streamlit.app/**

### Upload your own CSV files or use built-in mock data and generate a complete retail analytics dashboard instantly.

---

# 📌 Overview

An enterprise-grade **Data Engineering & Analytics Platform** that automatically:

✅ Ingests raw retail datasets

✅ Performs data quality checks

✅ Cleans and transforms the data

✅ Builds a star-schema warehouse

✅ Generates business insights

✅ Produces interactive dashboards

✅ Exports reports and databases

---

# ✨ Features

## 📥 Dual Mode Data Ingestion

* Upload your own CSV files
* Use built-in mock datasets
* Automatic schema validation

---

## 🧹 Data Quality Engine

* Missing value handling
* Duplicate detection
* Negative quantity detection
* Revenue mismatch detection
* Invalid date handling
* Orphan key detection

---

## 🏗 ETL Pipeline

```text
Raw CSV Files
      │
      ▼
   Extract
      │
      ▼
   Validate
      │
      ▼
     Clean
      │
      ▼
   Transform
      │
      ▼
 Build Warehouse
      │
      ▼
  SQLite Database
      │
      ▼
 Business Dashboard
```

---

# 🏛 Architecture

```text
sales_data.csv
products.csv
stores.csv
       │
       ▼
 ┌────────────┐
 │   Extract  │
 └────────────┘
       │
       ▼
 ┌────────────┐
 │  Validate  │
 └────────────┘
       │
       ▼
 ┌────────────┐
 │    Clean   │
 └────────────┘
       │
       ▼
 ┌────────────┐
 │ Transform  │
 └────────────┘
       │
       ▼
 ┌────────────┐
 │   SQLite   │
 └────────────┘
       │
       ▼
 ┌────────────┐
 │ Dashboard  │
 └────────────┘
```

---

# ⭐ Star Schema Warehouse

```text
dim_products
      ▲
      │
      │
fact_sales
      │
      ▼
dim_stores
```

### fact_sales

* sale_id
* store_id
* product_id
* quantity
* amount
* sale_date

### dim_products

* product_id
* product_name
* category
* price

### dim_stores

* store_id
* store_name
* city
* region

---

# 📊 Dashboard Features

### 📈 Revenue Trend Analysis

### 🏙 Revenue by City

### 🌎 Revenue by Region

### 🔥 Best Selling Products

### 📦 Product Performance Analysis

### 📋 Raw Data Explorer

### ⬇ Download Reports

### 🌙 Dark Mode

### 🔎 Dynamic Filters

* City
* Region
* Product
* Date Range
* Revenue Range

---

# 🧪 Data Quality Pitfall Mitigations

| # | Pitfall               | Resolution             |
| - | --------------------- | ---------------------- |
| 1 | Revenue mismatch      | Quarantine records     |
| 2 | Orphan dimension keys | Anti-join validation   |
| 3 | Invalid dates         | Coerce + quarantine    |
| 4 | Duplicate conflicts   | Conflict logging       |
| 5 | Negative quantities   | Exclude from warehouse |

---

# 📂 Project Structure

```text
retail-data-pipeline/
│
├── data/
├── database/
├── logs/
├── quarantine/
├── reports/
├── src/
│   ├── extract.py
│   ├── validate.py
│   ├── clean.py
│   ├── transform.py
│   ├── load.py
│   ├── report.py
│   └── app.py
│
├── main.py
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# 🚀 Quick Start

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/retail-data-pipeline.git
cd retail-data-pipeline
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Pipeline

```bash
python main.py
```

---

## Run Dashboard

```bash
streamlit run src/app.py
```

---

# 🐳 Docker

```bash
docker build -t retail-pipeline .
docker run -p 8501:8501 retail-pipeline
```

Open:

```text
http://localhost:8501
```

---

# 📈 Power BI Integration

1. Download `retail.db`
2. Connect via SQLite ODBC Driver
3. Import:

* fact_sales
* dim_products
* dim_stores

Create DAX Measures:

```DAX
Total Revenue =
SUM(fact_sales[amount])
```

```DAX
AOV =
DIVIDE(
    [Total Revenue],
    DISTINCTCOUNT(fact_sales[sale_id])
)
```

---

# 🏆 Business Insights Generated

✅ Top Selling Products

✅ Revenue by City

✅ Revenue by Region

✅ Daily Revenue Trends

✅ Store Performance

✅ Product Performance

---

# 🛠 Tech Stack

* Python
* Pandas
* NumPy
* SQLite
* SQLAlchemy
* Streamlit
* Plotly
* Docker
* Power BI

---


---

# 👨‍💻 Author

**Laksh Vyas**

Data Engineering | Machine Learning | Software Engineering

Built as a production-style Data Engineering assignment demonstrating ETL, Data Warehousing, Analytics Engineering, and Business Intelligence.
