# CRM Analytics for German Language Online School

**End-to-end marketing and sales analytics project** featuring interactive dashboard, automated reporting pipeline, and data-driven recommendations for business growth.

## ⚠️ CRITICAL: Data Limitations & Metrics

### Product-level CPA/ROAS — NOT accurately calculable!

**Problem**: Data lacks **Spend → Product attribution**. One advertising source generates leads for MULTIPLE products simultaneously.

**What's known:**
- `Spend` is aggregated by `Source + Campaign`
- `Deals` are tracked by `Source + Campaign + Product`

**What this means:**
```
Source: Instagram, Campaign: "Spring2024", Spend: €10,000
├─ Web Developer: 50 leads → 10 paid
├─ Digital Marketing: 100 leads → 20 paid
└─ UX/UI Design: 30 leads → 5 paid

❓ How much of €10,000 went to each product? → ❌ UNKNOWN
```

**Product-level metrics:**
- ✅ **Available**: Revenue, AOV, Paid Rate, Volume (# of paid deals)
- ❌ **Not available**: CPA, CPL, ROAS (requires spend allocation)

**See details**: [DISCLAIMER_PRODUCT_METRICS.md](reports/DISCLAIMER_PRODUCT_METRICS.md)

---

## About the Project

Comprehensive marketing and sales effectiveness analysis for a German language online school, based on CRM data (deals, contacts, calls) and advertising spend.

**Objectives**:
- Evaluate advertising channel effectiveness (CPL, CPA, ROAS)
- Build sales funnel and identify bottlenecks
- Analyze call-to-conversion relationship
- Perform product and geographic segmentation
- Create interactive dashboard and presentation for stakeholders

**Data**: 4 tables (Contacts, Calls, Deals, Spend) covering 2023-2024, ~21K deals, ~96K calls, ~19K contacts.

---

## Project Structure

```
.
├── data/
│   └── clean/              # Cleaned data (Parquet + CSV)
├── notebooks/              # Jupyter notebooks for exploration
│   └── 02_eda_metrics.ipynb
├── scripts/                # Pipeline scripts (01-09)
│   ├── 01_clean_export.py  # Data cleaning + flags (is_paid, is_duplicate_lost)
│   ├── 02_eda_metrics.py   # Overall metrics, funnel, time series
│   ├── 02b_duplicate_lost_analysis.py  # Duplicate analysis (CRITICAL)
│   ├── 03_descriptives_quality.py      # Descriptive stats + visualizations
│   ├── 04_time_analysis.py             # Time-to-close, seasonality
│   ├── 04b_calls_deals_link.py         # Calls-deals linkage (CRITICAL)
│   ├── 05_metrics_tree.py              # Metrics tree with Sankey diagrams
│   ├── 06_segmentation.py              # Product & geo segmentation
│   ├── 07_build_report.py              # Markdown report generation
│   ├── 08_make_presentation.py         # PPTX/HTML slides generation
│   └── 09_export_pdf.py                # PDF export (optional)
├── reports/                # All analysis outputs
│   ├── quality/            # Descriptive statistics (tables + figures)
│   ├── eda/                # EDA metrics, funnel, time series
│   ├── time/               # Time analysis (time-to-close, seasonality)
│   ├── metrics_tree/       # Metrics tree (Sankey + block diagrams)
│   ├── calls_deals/        # Calls-deals analysis
│   ├── segments/           # Product & geo segmentation
│   ├── insights/           # Insights (optional)
│   └── final/              # Final report + presentation
├── app.py                  # Streamlit dashboard
├── requirements.txt        # Python dependencies
├── task.md                 # Project requirements (source of truth)
└── README.md               # This file
```

---

## Quick Start

### 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Run full pipeline

```powershell
# Step 1: Data cleaning (required)
python scripts/01_clean_export.py

# Step 2: Core metrics and EDA
python scripts/02_eda_metrics.py

# Step 2b: Duplicate analysis (critical!)
python scripts/02b_duplicate_lost_analysis.py

# Step 3: Descriptive statistics with visualizations
python scripts/03_descriptives_quality.py

# Step 4: Time analysis
python scripts/04_time_analysis.py

# Step 4b: Calls-deals linkage (critical!)
python scripts/04b_calls_deals_link.py

# Step 5: Metrics tree with Sankey
python scripts/05_metrics_tree.py

# Step 6: Segmentation
python scripts/06_segmentation.py

# Step 7: Report generation
python scripts/07_build_report.py

# Step 8: Presentation
python scripts/08_make_presentation.py
```

### 3. Launch dashboard

```powershell
streamlit run app.py
```

Opens interactive dashboard with 8+ tabs:
- Overview (KPIs)
- Ads Performance
- Sales Funnel
- Products
- Payments
- Geography
- Time Analysis
- Notes & Methodology

---

## Key Artifacts

### Metrics & Analytics

- **Overall metrics**: `reports/eda/metrics_overall.json` — Spend, Deals, Paid Rate, Revenue
- **Metrics tree**: `reports/metrics_tree/metrics_tree_overall_overlap_window.json` — CPL, CPA, ROAS breakdown
- **Duplicates**: `reports/eda/duplicate_lost_impact.json` — Duplicate impact on metrics (8% of deals, +0.35 pp on paid rate)
- **Calls-deals linkage**: `reports/calls_deals/coverage_stats.json` — 95.78% deals with calls, avg 17.5 calls/deal

### Visualizations

- **Sankey metrics tree**: `reports/metrics_tree/figures/sankey_overall.png`
- **Stage funnel**: `reports/eda/figures/stage_funnel_top12.png`
- **Time series**: `reports/eda/figures/deals_paid_timeseries.png`
- **Calls vs Paid Rate**: `reports/calls_deals/figures/calls_vs_paid_rate.png`
- **13+ additional charts** in `reports/quality/figures/` and `reports/eda/figures/`

### Reports

- **Final report**: `reports/final/report.md`
- **Presentation**: `reports/final/slides.html` (opens in browser)
- **Presentation outline**: `reports/final/presentation_outline.md`

---

## Important: Contact ID Corruption

In source data `Calls.CONTACTID` and `Deals.Contact Name` IDs are stored as numbers in Excel, causing loss of trailing digits due to float precision limits.

The script preserves:
- `contact_id_str` — restored via rounding (may be imprecise)
- `contact_id15` — first 15 digits for "soft" joins (not unique, collisions possible)

For accurate joins, rely on `Deals` + `Spend` by `source/campaign` and time, using Calls in aggregate.

---

## Critical Rules (from task.md)

1. **Paid definition**: `Stage == "Payment Done"` (case-insensitive) → `is_paid = True`
2. **Duplicate Lost**: `Lost Reason == "Duplicate"` → NOT a real loss, but contact duplicate. Flag `is_duplicate_lost` is created automatically and **must be excluded** from churn analysis.
3. **Quality field**: Subjective manager assessment, do not use as direct predictor of conversion.
4. **Revenue**: 
   - `revenue_cash` — actually received money
   - `revenue_contract` — full contract value (used for ROAS)

---

## Known Limitations

1. **Contact ID corruption**: Excel float limitations make reliable Contacts→Calls→Deals joins unreliable. Use aggregate analysis by source/time.

2. **Time lag between Spend and Deals**: Ad spend converts to deals with 3-7 day delay. ROAS calculations require time window adjustments.

3. **Missingness in Campaign/City**: ~20-30% missing in optional fields. Analysis filtered by `min_deals` for statistical significance.

4. **Quality field subjectivity**: Lead quality assessment ("A", "B", "C") is manager's personal opinion, do not use for predictive models without validation.

---

## Technologies

- **Python 3.11+**
- **Data**: pandas, numpy, pyarrow (Parquet)
- **Visualization**: plotly, matplotlib, seaborn, kaleido
- **Dashboard**: streamlit
- **Presentation**: python-pptx, markdown, playwright (PDF export)
- **Notebooks**: jupyter

---

## Author

Project completed as a final assignment for the Data Analytics course.

---

## Changelog

- **v1.3** (2024-01): ✅ Added critical components: Sankey visualizations, descriptive statistics charts, mode in metrics, calls-deals relationship analysis, duplicate analysis, conclusions in all READMEs
- **v1.2** (2024-01): Dashboard + presentation
- **v1.1** (2024-01): Pipeline scripts 01-08
- **v1.0** (2024-01): Initial version with data cleaning
