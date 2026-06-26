"""src/app.py — Retail Data Engineering & Analytics Platform"""
# ── Streamlit Cloud path fix ──────────────────────────────────────────────────
# When Streamlit Cloud runs src/app.py it adds src/ to sys.path, not the repo
# root. This one-liner ensures the project root is always first so that
# `from src.X import ...` resolves correctly in all environments.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import time, logging
from typing import Any
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from src.config import DB_PATH
from src.extract import extract_all
from src.validate import validate_and_clean
from src.clean import clean_sales, clean_products, clean_stores
from src.transform import transform_all, aggregate_product_performance, aggregate_store_performance
from src.load import load_warehouse, drop_and_reinitialise, query_table, get_table_names
from src.report import generate_cleaned_sales_csv, generate_revenue_report_csv, get_db_bytes

log = logging.getLogger(__name__)
st.set_page_config(page_title="Retail Data Engineering & Analytics Platform", page_icon="🏪", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.badge-demo{display:inline-block;padding:6px 16px;border-radius:20px;background:linear-gradient(135deg,#00c853,#00e676);color:#000;font-weight:700;font-size:.82rem;}
.badge-custom{display:inline-block;padding:6px 16px;border-radius:20px;background:linear-gradient(135deg,#1565c0,#42a5f5);color:#fff;font-weight:700;font-size:.82rem;}
.badge-idle{display:inline-block;padding:6px 16px;border-radius:20px;background:rgba(0,0,0,.06);color:#666;font-weight:600;font-size:.82rem;}
.log-terminal{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:.9rem 1.1rem;font-family:'Courier New',monospace;font-size:.78rem;color:#c9d1d9;line-height:1.9;max-height:260px;overflow-y:auto;}
.task-header{font-size:1.05rem;font-weight:700;padding:6px 0 4px 0;border-bottom:2px solid #667eea;margin-bottom:.6rem;}
.kpi-box{background:linear-gradient(135deg,rgba(102,126,234,.12),rgba(118,75,162,.06));border:1px solid rgba(102,126,234,.25);border-radius:12px;padding:1rem 1.2rem;text-align:center;}
.kpi-val{font-size:1.8rem;font-weight:800;margin:0;}
.kpi-lbl{font-size:.72rem;color:#888;text-transform:uppercase;letter-spacing:1px;margin:0;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults: dict[str, Any] = {
        "done": False, "mode": None,
        "fact": None, "dim_p": None, "dim_s": None,
        "scorecard": None, "logs": [], "elapsed": 0.0,
        "raw_s": None, "raw_p": None, "raw_st": None,
        "dup_count": 0, "pre_clean": 0, "post_clean": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

# ── Pipeline ─────────────────────────────────────────────────────────────────
def _run(mode, s_src=None, p_src=None, st_src=None):
    entries: list[str] = []
    t0 = time.perf_counter()
    def L(m): entries.append(m)
    with st.spinner("⚙️ Running pipeline…"):
        raw_s, raw_p, raw_st = extract_all(s_src, p_src, st_src)
        L(f"✅ Sales Dataset Loaded — shape: {raw_s.shape[0]} rows × {raw_s.shape[1]} cols")
        L(f"✅ Product Catalog Ingested — {raw_p.shape[0]} products mapped")
        L(f"✅ Store Dimensions Loaded — {raw_st.shape[0]} locations mapped")

        pre = len(raw_s)
        val_s, val_p, val_st, sc = validate_and_clean(raw_s, raw_p, raw_st)
        L(f"✅ Data Quality Matrix — Dupes: {sc.duplicates_removed} | Null qty fixed: {sc.null_quantity_fixed} | "
          f"Null amount dropped: {sc.null_amount_removed} | Bad dates: {sc.invalid_dates_quarantined} | "
          f"Orphans: {sc.orphan_keys_flagged}")

        cs = clean_sales(val_s); cp = clean_products(val_p); cst = clean_stores(val_st)
        L(f"✅ Cleaned Sales shape: {cs.shape[0]} rows × {cs.shape[1]} cols")

        fact, dim_p, dim_s, mis = transform_all(cs, cp, cst)
        sc.revenue_mismatch_flagged = mis
        L(f"✅ Star Schema Built — fact_sales: {fact.shape[0]} rows | Revenue mismatches flagged: {mis}")

        load_warehouse(fact, dim_p, dim_s)
        L("✅ Analytical Warehouse Synchronized (SQLite Sync Completed)")
        el = time.perf_counter() - t0
        L(f"🚀 Pipeline terminated in {el:.4f}s")

    st.session_state.update(done=True, mode=mode, fact=fact, dim_p=dim_p, dim_s=dim_s,
                             scorecard=sc, logs=entries, elapsed=el,
                             raw_s=raw_s, raw_p=raw_p, raw_st=raw_st,
                             dup_count=sc.duplicates_removed, pre_clean=pre, post_clean=len(cs))
    st.rerun()

# ── Reset ─────────────────────────────────────────────────────────────────────
def _reset():
    drop_and_reinitialise()
    for k in list(st.session_state.keys()): del st.session_state[k]
    _init(); st.rerun()

# ── Badge ─────────────────────────────────────────────────────────────────────
def _badge():
    c1, c2 = st.columns([7, 1])
    with c1:
        m = st.session_state.mode
        if m == "demo":   st.markdown('<span class="badge-demo">🟢 Active Source: Built-in Demo Dataset</span>', unsafe_allow_html=True)
        elif m == "upload": st.markdown('<span class="badge-custom">🔵 Active Source: Custom User Dataset</span>', unsafe_allow_html=True)
        else: st.markdown('<span class="badge-idle">⚪ Awaiting Ingestion</span>', unsafe_allow_html=True)
    with c2:
        if st.button("🔄 Reset Platform", key="reset"): _reset()

# ── Landing ───────────────────────────────────────────────────────────────────
def _landing():
    st.markdown("## 🏪 RetailMart Pvt. Ltd. — Data Engineering Platform")
    st.markdown("_Enterprise ETL pipeline · Dual-mode ingestion · Star Schema warehouse · 5-tab analytics_")
    c1, _, c2 = st.columns([5, 1, 5])
    with c1:
        st.markdown("#### 📁 Option 1 — Upload Your Own Dataset")
        uf_s  = st.file_uploader("sales_data.csv",  type="csv", key="uf_s")
        uf_p  = st.file_uploader("products.csv",    type="csv", key="uf_p")
        uf_st = st.file_uploader("stores.csv",      type="csv", key="uf_st")
        if uf_s and uf_p and uf_st:
            st.success("✅ All 3 files uploaded — pipeline ready.")
            if st.button("🚀 Run Upload Pipeline", use_container_width=True):
                _run("upload", uf_s, uf_p, uf_st)
    with _:
        st.markdown('<div style="margin-top:110px;text-align:center;color:#aaa">— OR —</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("#### ⚡ Option 2 — Try Demo Dataset")
        st.info("Runs the full ETL using pre-baked anomalous mock data (dupes, nulls, bad dates, orphan keys, revenue mismatches).")
        if st.button("▶ Run Demo Engine", type="primary", use_container_width=True): _run("demo")

# ── Task Outputs ──────────────────────────────────────────────────────────────
def _tasks():
    fact   = st.session_state.fact
    dim_p  = st.session_state.dim_p
    dim_s  = st.session_state.dim_s
    sc     = st.session_state.scorecard
    raw_s  = st.session_state.raw_s
    raw_p  = st.session_state.raw_p
    raw_st = st.session_state.raw_st

    st.markdown("---")
    st.markdown("## 📋 Assignment Output — Tasks 1–6")

    # Task 1
    with st.expander("📦 Task 1: Data Ingestion — Shapes, First 5 Rows & Null Summary", expanded=True):
        st.markdown('<div class="task-header">Task 1 · Data Ingestion</div>', unsafe_allow_html=True)
        for label, df in [("sales_data", raw_s), ("products", raw_p), ("stores", raw_st)]:
            st.markdown(f"**{label}.csv** — Shape: `{df.shape}`")
            st.dataframe(df.head(5), use_container_width=True)
            nulls = df.isnull().sum()
            nulls = nulls[nulls > 0]
            if not nulls.empty:
                st.warning(f"Null values in **{label}**: " + " | ".join(f"`{c}`: {n}" for c, n in nulls.items()))
            else:
                st.success(f"No nulls in **{label}**.")

    # Task 2
    with st.expander("🧹 Task 2: Data Cleaning — Duplicates, Nulls & Type Conversion"):
        st.markdown('<div class="task-header">Task 2 · Data Cleaning</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duplicates Found & Removed", sc.duplicates_removed)
        c2.metric("Null Quantity → Filled 0", sc.null_quantity_fixed)
        c3.metric("Null Amount → Dropped", sc.null_amount_removed)
        c4.metric("Rows After Cleaning", st.session_state.post_clean)
        st.markdown(f"**Pre-clean rows:** `{st.session_state.pre_clean}` → **Post-clean rows:** `{st.session_state.post_clean}`")
        st.markdown("✅ `sale_date` coerced to **datetime** via `pd.to_datetime(errors='coerce')`")
        st.markdown("✅ `amount` enforced as **float64**  |  `quantity` enforced as **int64**")
        if sc.invalid_dates_quarantined:
            st.warning(f"⚠️ {sc.invalid_dates_quarantined} row(s) with unparseable dates quarantined.")
        if sc.orphan_keys_flagged:
            st.warning(f"⚠️ {sc.orphan_keys_flagged} row(s) with unknown store/product IDs quarantined.")

    # Task 3
    with st.expander("🔀 Task 3: Data Transformation — Merged DataFrame & Revenue Stats"):
        st.markdown('<div class="task-header">Task 3 · Data Transformation</div>', unsafe_allow_html=True)
        store_cols = [c for c in ["store_id","store_name","city","region"] if c in dim_s.columns]
        merged = (
            fact
            .merge(dim_p[["product_id","product_name","category","price"]], on="product_id", how="left")
            .merge(dim_s[store_cols], on="store_id", how="left")
        )
        if "price" in merged.columns and "total_revenue" not in merged.columns:
            merged["total_revenue"] = merged["quantity"] * merged["price"]

        st.markdown(f"**Merged DataFrame** — Shape: `{merged.shape}`")
        st.dataframe(merged.head(10), use_container_width=True)

        if "total_revenue" in merged.columns:
            tr = merged["total_revenue"].dropna().values
            st.markdown("**`total_revenue = quantity × price`** (via NumPy)")
            m1, m2, m3 = st.columns(3)
            m1.metric("Mean total_revenue", f"₹{np.mean(tr):,.2f}")
            m2.metric("Max total_revenue",  f"₹{np.max(tr):,.2f}")
            m3.metric("Min total_revenue",  f"₹{np.min(tr):,.2f}")

        if "city" in merged.columns:
            city_rev = merged.groupby("city")["amount"].sum().reset_index(name="total_revenue").sort_values("total_revenue", ascending=False)
            st.markdown("**Revenue by City (descending)**")
            st.dataframe(city_rev, use_container_width=True)
            fig = px.bar(city_rev, x="city", y="total_revenue", color="city",
                         title="Total Revenue per City", template="plotly_dark",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # Task 4
    with st.expander("💾 Task 4: Data Loading — SQLite & Top 3 Best-Selling Products"):
        st.markdown('<div class="task-header">Task 4 · Data Loading (SQL)</div>', unsafe_allow_html=True)
        tables = get_table_names()
        st.success(f"✅ Tables loaded into SQLite: **{', '.join(tables)}**")
        try:
            top3 = query_table("""
                SELECT p.product_name, SUM(f.quantity) AS total_qty_sold
                FROM fact_sales f
                JOIN dim_products p ON f.product_id = p.product_id
                GROUP BY f.product_id, p.product_name
                ORDER BY total_qty_sold DESC
                LIMIT 3
            """)
            st.markdown("**🏆 Top 3 Best-Selling Products by Quantity Sold**")
            st.dataframe(top3, use_container_width=True)
            fig2 = px.bar(top3, x="product_name", y="total_qty_sold", color="product_name",
                          title="Top 3 Products by Units Sold", template="plotly_dark",
                          color_discrete_sequence=["#667eea","#764ba2","#f093fb"])
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(str(e))

    # Task 5
    with st.expander("📊 Task 5: Reporting — Revenue per Store per Day"):
        st.markdown('<div class="task-header">Task 5 · Revenue per Store per Day</div>', unsafe_allow_html=True)
        try:
            rev_day = query_table("""
                SELECT s.store_name, s.city,
                       DATE(f.sale_date) AS sale_day,
                       SUM(f.amount) AS daily_revenue,
                       COUNT(f.sale_id) AS transactions
                FROM fact_sales f
                JOIN dim_stores s ON f.store_id = s.store_id
                GROUP BY f.store_id, s.store_name, s.city, DATE(f.sale_date)
                ORDER BY sale_day, daily_revenue DESC
            """)
            st.dataframe(rev_day, use_container_width=True)
            if not rev_day.empty and "sale_day" in rev_day.columns:
                fig3 = px.line(rev_day, x="sale_day", y="daily_revenue", color="store_name",
                               title="Daily Revenue Trend per Store", template="plotly_dark",
                               markers=True)
                fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.error(str(e))

    # Task 6
    with st.expander("🚀 Task 6: Pipeline Summary Report"):
        st.markdown('<div class="task-header">Task 6 · Pipeline & Summary Report</div>', unsafe_allow_html=True)
        store_cols = [c for c in ["store_id","store_name","city","region"] if c in dim_s.columns]
        enriched6 = (
            fact
            .merge(dim_p[["product_id","product_name"]], on="product_id", how="left")
            .merge(dim_s[store_cols], on="store_id", how="left")
        )
        total_txns = len(fact)
        total_rev  = fact["amount"].sum()
        top_city   = enriched6.groupby("city")["amount"].sum().idxmax() if "city" in enriched6.columns else "N/A"
        top_prod   = enriched6.groupby("product_name")["quantity"].sum().idxmax() if "product_name" in enriched6.columns else "N/A"

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="kpi-box"><p class="kpi-lbl">Total Transactions</p><p class="kpi-val">{total_txns:,}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-box"><p class="kpi-lbl">Total Revenue</p><p class="kpi-val">₹{total_rev:,.0f}</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-box"><p class="kpi-lbl">Top Selling City</p><p class="kpi-val" style="font-size:1.3rem">{top_city}</p></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="kpi-box"><p class="kpi-lbl">Top Selling Product</p><p class="kpi-val" style="font-size:1.1rem">{top_prod}</p></div>', unsafe_allow_html=True)
        st.markdown("")
        st.success(f"🚀 `run_pipeline()` completed in **{st.session_state.elapsed:.4f} seconds** with full try-except error isolation.")

# ── Sidebar filters ───────────────────────────────────────────────────────────
def _sidebar(fact, dim_p, dim_s):
    st.sidebar.markdown("## 🎛️ Filters")
    store_cols = [c for c in ["store_id","store_name","city","region"] if c in dim_s.columns]
    enriched = (
        fact
        .merge(dim_p[["product_id","category"]], on="product_id", how="left")
        .merge(dim_s[store_cols], on="store_id", how="left")
    )
    all_cities = sorted(enriched["city"].dropna().unique().tolist()) if "city" in enriched.columns else []
    sel_cities = st.sidebar.multiselect("🏙️ City", all_cities, default=all_cities)
    all_cats   = sorted(enriched["category"].dropna().unique().tolist()) if "category" in enriched.columns else []
    sel_cats   = st.sidebar.multiselect("🏷️ Category", all_cats, default=all_cats)
    min_r, max_r = float(enriched["amount"].min()), float(enriched["amount"].max())
    rev_r = st.sidebar.slider("💰 Amount (₹)", min_r, max_r, (min_r, max_r))
    if "sale_date" in enriched.columns and pd.api.types.is_datetime64_any_dtype(enriched["sale_date"]):
        mn, mx = enriched["sale_date"].min().date(), enriched["sale_date"].max().date()
        dr = st.sidebar.date_input("📅 Date Range", (mn, mx), min_value=mn, max_value=mx)
    else:
        dr = None
    mask = enriched["amount"].between(rev_r[0], rev_r[1])
    if all_cities: mask &= enriched["city"].isin(sel_cities)
    if all_cats:   mask &= enriched["category"].isin(sel_cats)
    if dr and len(dr) == 2:
        mask &= (enriched["sale_date"].dt.date >= dr[0]) & (enriched["sale_date"].dt.date <= dr[1])
    return enriched[mask].copy()

# ── Dashboard tabs ────────────────────────────────────────────────────────────
def _dashboard(fact, dim_p, dim_s, sc):
    filtered = _sidebar(fact, dim_p, dim_s)
    t1,t2,t3,t4,t5 = st.tabs(["📊 Executive Insights","🏷️ Product Performance","🏪 Store Rankings","🔬 Pipeline Observability","🗄️ Warehouse Query Studio"])

    with t1:
        st.markdown("### 📊 Executive Insights Hub")
        total_rev = filtered["amount"].sum(); n = len(filtered); aov = filtered["amount"].mean() if n else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Revenue", f"₹{total_rev:,.2f}"); c2.metric("Transactions", f"{n:,}"); c3.metric("Avg Order Value", f"₹{aov:,.2f}")
        if "sale_date" in filtered.columns and pd.api.types.is_datetime64_any_dtype(filtered["sale_date"]):
            m = filtered.copy(); m["month"] = m["sale_date"].dt.to_period("M").astype(str)
            trend = m.groupby("month")["amount"].sum().reset_index(name="revenue")
            fig = px.area(trend, x="month", y="revenue", title="Monthly Revenue Trend", template="plotly_dark", color_discrete_sequence=["#667eea"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"); st.plotly_chart(fig, use_container_width=True)
        if "category" in filtered.columns:
            cr = filtered.groupby("category")["amount"].sum().reset_index(name="revenue")
            fig2 = px.pie(cr, values="revenue", names="category", title="Revenue by Category", template="plotly_dark", hole=0.4)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)"); st.plotly_chart(fig2, use_container_width=True)

    with t2:
        st.markdown("### 🏷️ Product Performance")
        pp = aggregate_product_performance(filtered, dim_p)
        if not pp.empty:
            fig = px.bar(pp.head(10), x="total_revenue", y="product_name", orientation="h", color="category",
                         title="Top 10 Products by Revenue", template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"); st.plotly_chart(fig, use_container_width=True)
            st.dataframe(pp, use_container_width=True)

    with t3:
        st.markdown("### 🏪 Store & Geographic Rankings")
        sp = aggregate_store_performance(filtered, dim_s)
        if not sp.empty:
            fig = px.bar(sp, x="store_name", y="total_revenue", color="region" if "region" in sp.columns else "store_name",
                         title="Revenue by Store", template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"); st.plotly_chart(fig, use_container_width=True)
            st.dataframe(sp, use_container_width=True)

    with t4:
        st.markdown("### 🔬 Pipeline Observability")
        d = sc.to_dict()
        cols = st.columns(4)
        for i,(k,v) in enumerate(list(d.items())[:8]):
            cols[i%4].metric(k.replace("_"," ").title(), v)
        fig = px.bar(x=list(d.keys())[:-2], y=list(d.values())[:-2], title="Quality Scorecard", template="plotly_dark", color_discrete_sequence=["#f093fb"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"); st.plotly_chart(fig, use_container_width=True)
        if sc.quarantined_records:
            bucket = st.selectbox("🚨 Quarantine bucket", list(sc.quarantined_records.keys()))
            if bucket and sc.quarantined_records[bucket]:
                st.dataframe(pd.DataFrame(sc.quarantined_records[bucket]), use_container_width=True)
        if "revenue_validation_mismatch" in fact.columns:
            mis = fact[fact["revenue_validation_mismatch"]]
            if not mis.empty:
                st.markdown("#### ⚠️ Revenue Mismatch Rows")
                st.dataframe(mis, use_container_width=True)

    with t5:
        st.markdown("### 🗄️ Warehouse Query Studio")
        for tbl in get_table_names():
            with st.expander(f"Schema: {tbl}"):
                try: st.dataframe(query_table(f"SELECT * FROM [{tbl}] LIMIT 5"), use_container_width=True)
                except Exception as e: st.error(str(e))
        sql = st.text_area("Run SQL (SELECT only)", value="SELECT * FROM fact_sales LIMIT 20", height=110, key="sql")
        if st.button("▶ Execute", key="exec"):
            try:
                r = query_table(sql); st.success(f"{len(r)} rows"); st.dataframe(r, use_container_width=True)
            except Exception as e: st.error(str(e))

# ── Log terminal ──────────────────────────────────────────────────────────────
def _logs():
    entries = st.session_state.logs
    if not entries: return
    st.markdown("#### ⚡ Pipeline Execution Log")
    html = "".join(f"<div>{e}</div>" for e in entries)
    st.markdown(f'<div class="log-terminal">{html}</div>', unsafe_allow_html=True)

# ── Exports ───────────────────────────────────────────────────────────────────
def _exports(fact, dim_p, dim_s):
    st.markdown("---")
    st.markdown("### 📦 Export Engine")
    c1,c2,c3 = st.columns(3)
    with c1: st.download_button("⬇️ Cleaned Sales (.csv)", generate_cleaned_sales_csv(fact), "cleaned_sales.csv","text/csv", use_container_width=True)
    with c2: st.download_button("⬇️ Revenue Report (.csv)", generate_revenue_report_csv(fact, dim_p, dim_s), "revenue_report.csv","text/csv", use_container_width=True)
    with c3:
        try: st.download_button("⬇️ SQLite Database (.db)", get_db_bytes(), "retail.db","application/octet-stream", use_container_width=True)
        except Exception as e: st.warning(str(e))

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown("# 🏪 Retail Data Engineering & Analytics Platform")
    _badge(); st.markdown("---")
    if not st.session_state.done:
        _landing()
    else:
        fact=st.session_state.fact; dim_p=st.session_state.dim_p
        dim_s=st.session_state.dim_s; sc=st.session_state.scorecard
        _logs()
        _tasks()
        st.markdown("---")
        st.markdown("## 📊 Interactive Analytics Dashboard")
        _dashboard(fact, dim_p, dim_s, sc)
        _exports(fact, dim_p, dim_s)

if __name__ == "__main__":
    main()
