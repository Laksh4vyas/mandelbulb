
# Retail Data Engineering & Analytics Platform


An enterprise-grade ETL pipeline with a dual-mode Streamlit analytics portal, star-schema SQLite warehouse, and built-in data quality enforcement.

LIVE  URL - https://mandelbulb-4omxqtuh369sbcxvj37rtn.streamlit.app/


---


## Architecture



```

raw CSV  →  extract  →  validate  →  clean  →  transform  →  load (SQLite)

                             ↓ scorecard telemetry

                        Streamlit 5-Tab Dashboard

```



**Star Schema**

- `fact_sales` — transactional measurements + FK references  

- `dim_products` — product catalog dimension  

- `dim_stores` — store/geography dimension  



---



## Quick Start



```bash

# 1. Install dependencies

pip install -r requirements.txt



# 2. Run via CLI (demo mode)

python main.py



# 3. Launch Streamlit UI

streamlit run src/app.py

```



**Docker**

```bash

docker build -t retail-pipeline .

docker run -p 8501:8501 retail-pipeline

# Open http://localhost:8501

```



---



## Five Zero-Day Pitfall Mitigations




| # | Pitfall | Resolution |

|---|---------|------------|



| 1 | Revenue mismatch (`amount ≠ qty × price`) | Flag `revenue_validation_mismatch=True`; export to `quarantine/revenue_mismatch.csv` |



| 2 | Orphan dimension keys | Anti-join against `dim_products` / `dim_stores`; isolate to `quarantine/orphan_keys.csv` |

| 3 | Unparseable / bad dates | `pd.to_datetime(errors="coerce")` → quarantine to `quarantine/invalid_dates.csv` |

| 4 | Conflicting metrics on duplicate `sale_id` | Detect multi-value groups before dedup; log conflict count in scorecard |

| 5 | Negative / null quantity | Null imputed to 0; negatives quarantined and excluded from fact table |







---


## Power BI Integration



1. Download `retail.db` from the **Export Engine** tab.  

2. In Power BI Desktop → **Get Data** → **ODBC** → point to the `.db` file via the SQLite ODBC driver.  

3. Import tables: `fact_sales`, `dim_products`, `dim_stores`.  

4. In **Model View**, draw relationships:  

   - `fact_sales[product_id]` → `dim_products[product_id]` (Many-to-One)  

   - `fact_sales[store_id]` → `dim_stores[store_id]` (Many-to-One)  

6.

7. Example DAX measure:

```dax

Tot

al Revenue = SUM(fact_sales[amount])



AOV = DIVIDE([Total Revenue], DISTINCTCOUNT(fact_sales[sale_id]))

Revenue MoM % = 

  DIVIDE(

    [Total Revenue] - CALCULATE([Total Revenue], PREVIOUSMONTH(fact_sales[sale_date])),

    CALCULATE([Total Revenue], PREVIOUSMONTH(fact_sales[sale_date]))

  )

```



---



## Directory Layout



```

retail-data-pipeline/
├── data/               # Pre-baked mock CSVs (anomalous test data)

├── database/           # SQLite warehouse (retail.db)

├── logs/               # Pipeline execution logs

├── quarantine/         # Isolated bad records

├── reports/            # Generated CSV reports

├── src/

│   ├── config.py       # Env-agnostic path resolution



│   ├── extract.py      # Dual-mode ingestion engine


│   ├── validate.py     # Quality gateway + scorecard

│   ├── clean.py        # Cosmetic normalisation

│   ├── transform.py    # Star schema builder

│   ├── load.py         # SQLAlchemy warehouse writer

│   ├── report.py       # Export engine

│   └── app.py          # Streamlit 5-tab portal

├── main.py             # CLI orchestrator

├── Dockerfile

└── requirements.txt

```

#
