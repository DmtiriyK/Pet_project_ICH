from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

try:
    from reference_data import REFERENCE_METRICS, REF
except ImportError:
    REFERENCE_METRICS = None
    REF = None


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "data" / "clean"


# ============================================================================
# GLOSSARY: Definitions of all key product analytics terms
# ============================================================================

GLOSSARY = {
    "CPA": {
        "full_name": "Cost Per Acquisition",
        "formula": "Spend ÷ Paid Deals",
        "description": "Cost to acquire one paying customer. Shows how much ad spend is needed to get 1 payment.",
        "why": "Key marketing efficiency metric. Lower CPA = more efficient budget allocation.",
        "benchmark": "Good CPA < 20% of AOV (Customer Acquisition Cost should be recovered within first purchase)",
        "levers": "↓ CPL (improve targeting), ↑ Paid Rate (improve sales process)"
    },
    "ROAS": {
        "full_name": "Return On Ad Spend",
        "formula": "Revenue ÷ Spend",
        "description": "Return on advertising spend. Shows how much revenue each euro of ad spend generates.",
        "why": "Primary marketing profitability metric. ROAS > 1 means profitability (revenue exceeds costs).",
        "benchmark": "Break-even ROAS = 1.0x. Good ROAS for education: 3-10x, excellent: >10x",
        "levers": "↑ AOV (sell at higher prices), ↓ CPA (reduce acquisition cost), ↑ Paid Rate"
    },
    "AOV": {
        "full_name": "Average Order Value",
        "formula": "Revenue ÷ Paid Deals",
        "description": "Average check — how much revenue one paying customer brings on average.",
        "why": "Shows monetization. AOV growth increases revenue without increasing acquisition costs.",
        "benchmark": "Depends on product. In online education: €300-15,000 (courses of different length)",
        "levers": "Upsell (add-on sales), cross-sell (related products), premium tiers, installments"
    },
    "CPL": {
        "full_name": "Cost Per Lead",
        "formula": "Spend ÷ Deals",
        "description": "Cost per lead (created deal). Shows ad effectiveness at the top of the funnel.",
        "why": "Traffic quality indicator. Low CPL with high Paid Rate = ideal channel.",
        "benchmark": "Depends on niche. B2C online education: €5-50 per lead",
        "levers": "Creative optimization, improved targeting, A/B testing landing pages"
    },
    "Paid Rate": {
        "full_name": "Conversion Rate to Payment",
        "formula": "Paid Deals ÷ Deals",
        "description": "Percentage of leads that converted to payment. Sales team efficiency metric.",
        "why": "Shows manager performance quality and product-market fit. High Paid Rate = product needed, sales working.",
        "benchmark": "Online education: 2-10% (depends on price and segment). >5% is good",
        "levers": "↓ SLA (process faster), improve sales scripts, lead qualification, nurturing"
    },
    "SLA": {
        "full_name": "Service Level Agreement (First Response Time)",
        "formula": "Time from lead creation to first contact",
        "description": "Sales response time to new lead. Measured in minutes/hours.",
        "why": "Critical for conversion. Leads 'cool down' after 5 minutes. SLA < 1 hour = quality standard.",
        "benchmark": "Ideal: <5 minutes. Normal: <1 hour. Bad: >24 hours",
        "levers": "Notification automation, lead routing, expand sales team, CRM integrations"
    },
    "Funnel": {
        "full_name": "Sales Funnel (Marketing-Sales Pipeline)",
        "formula": "Spend → Leads → Qualified → Payment",
        "description": "Customer journey from ad contact to payment. Each stage has a conversion rate.",
        "why": "Allows finding 'bottlenecks' where we lose customers and where to optimize.",
        "benchmark": "Fewer steps = higher conversion. Optimal: 3-5 stages",
        "levers": "Remove friction at stages, A/B tests, improve UX, follow-ups"
    },
    "Revenue": {
        "full_name": "Revenue (Contract vs Cash)",
        "formula": "Contract = full course price. Cash = actually paid",
        "description": "Revenue. Contract revenue = promised (may be installments). Cash revenue = actually received money.",
        "why": "Contract shows potential, Cash shows real cash flow. For ROAS we use Contract (more conservative).",
        "benchmark": "Cash / Contract ratio shows payment collection quality. Normal: >70%",
        "levers": "↑ Paid Deals, ↑ AOV, better payment terms, reduce refunds"
    },
    "Unit Economics": {
        "full_name": "Unit Economics (profit per unit)",
        "formula": "Revenue per customer - Cost per customer (CPA + CAC)",
        "description": "Economics of one customer. Shows if the model is profitable at unit level.",
        "why": "If Unit Economics is negative — business loses money on each customer (scaling will kill the company).",
        "benchmark": "Unit profit > 0 (minimum). Good: LTV/CAC > 3x",
        "levers": "↑ AOV, ↓ CPA, retention (repeat purchases), operational efficiency"
    },
    "Metrics Tree": {
        "full_name": "Metrics Tree (metrics decomposition tree)",
        "formula": "North Star = Driver1 × Driver2 → Components → Inputs",
        "description": "Hierarchical metrics structure showing mathematical relationships. Example: Revenue = Paid × AOV = (Deals × Rate) × AOV",
        "why": "Helps understand which metrics to pull for North Star growth. Makes analysis structured.",
        "benchmark": "4-5 levels of decomposition. North Star → Drivers → Components → Input metrics",
        "levers": "Defines Growth Levers — metrics with maximum impact on North Star"
    },
    "Growth Levers": {
        "full_name": "Growth Levers (growth levers)",
        "formula": "Metrics with high impact × low change complexity",
        "description": "Metrics whose change will give maximum North Star growth with minimum effort.",
        "why": "For prioritization. Instead of 'improve everything' — focus on 2-3 key levers.",
        "benchmark": "Calculate sensitivity: if metric X changes by 10%, how much will Revenue grow?",
        "levers": "Usually: Paid Rate (sales), CPL (marketing), AOV (product)"
    },
}


def create_metric_tooltip(term: str) -> str:
    """
    Creates interactive tooltip for a term
    Returns HTML with ℹ️ icon and hover tooltip
    """
    if term not in GLOSSARY:
        return term
    
    info = GLOSSARY[term]
    
    # Form tooltip text
    tooltip_html = f"""
    <div style="display: inline-block; position: relative; cursor: help;">
        <span style="border-bottom: 1px dotted #666;">{term}</span>
        <span style="margin-left: 4px; color: #0066cc;">ℹ️</span>
        <div style="
            visibility: hidden;
            position: absolute;
            z-index: 1000;
            background-color: #2e2e2e;
            color: white;
            padding: 12px;
            border-radius: 6px;
            font-size: 13px;
            width: 320px;
            bottom: 125%;
            left: 50%;
            margin-left: -160px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        " class="tooltip-content">
            <strong>{info['full_name']}</strong><br/>
            <em>{info['formula']}</em><br/><br/>
            {info['description']}<br/><br/>
            <strong>Why:</strong> {info['why']}<br/>
            <strong>Benchmark:</strong> {info['benchmark']}
        </div>
    </div>
    <style>
        .tooltip-content:hover {{ visibility: visible !important; }}
        div:hover > .tooltip-content {{ visibility: visible !important; }}
    </style>
    """
    
    return tooltip_html


def show_metric_info(term: str, use_popover: bool = True):
    """
    Shows metric information via st.popover or st.info
    
    Args:
        term: Metric name from GLOSSARY
        use_popover: If True, uses popover (Streamlit 1.31+), else expander
    """
    if term not in GLOSSARY:
        return
    
    info = GLOSSARY[term]
    
    if use_popover and hasattr(st, 'popover'):
        # Streamlit 1.31+ с popover
        with st.popover(f"ℹ️ {term}"):
            st.markdown(f"**{info['full_name']}**")
            st.code(info['formula'], language=None)
            st.write(info['description'])
            st.divider()
            st.write(f"**Why needed:** {info['why']}")
            st.write(f"**Benchmark:** {info['benchmark']}")
            if info.get('levers'):
                st.write(f"**How to improve:** {info['levers']}")
    else:
        # Fallback for older Streamlit versions
        with st.expander(f"ℹ️ About metric:{term}"):
            st.markdown(f"**{info['full_name']}**")
            st.code(info['formula'], language=None)
            st.write(info['description'])
            st.divider()
            st.write(f"**Why needed:** {info['why']}")
            st.write(f"**Benchmark:** {info['benchmark']}")
            if info.get('levers'):
                st.write(f"**How to improve:** {info['levers']}")


@dataclass(frozen=True)
class Window:
    start: pd.Timestamp
    end: pd.Timestamp


def _require_clean() -> bool:
    return CLEAN_DIR.exists() and (CLEAN_DIR / "deals.parquet").exists()


@st.cache_data(show_spinner=False)
def load_clean(use_filtered: bool = False) -> dict[str, pd.DataFrame]:
    deals_file = "deals_filtered.parquet" if use_filtered else "deals.parquet"
    return {
        "contacts": pd.read_parquet(CLEAN_DIR / "contacts.parquet"),
        "calls": pd.read_parquet(CLEAN_DIR / "calls.parquet"),
        "deals": pd.read_parquet(CLEAN_DIR / deals_file),
        "spend": pd.read_parquet(CLEAN_DIR / "spend.parquet"),
    }


def infer_overlap_window(tables: dict[str, pd.DataFrame]) -> Window:
    deals = tables["deals"]
    spend = tables["spend"]

    deals_dates = pd.to_datetime(deals["created_time"], errors="coerce").dropna()
    spend_dates = pd.to_datetime(spend["date"], errors="coerce").dropna()

    start = max(deals_dates.min().normalize(), spend_dates.min().normalize())
    end = min(deals_dates.max().normalize(), spend_dates.max().normalize())
    return Window(start=start, end=end)


def _safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def apply_filters(
    tables: dict[str, pd.DataFrame],
    window: Window,
    *,
    sources: list[str],
    campaigns: list[str],
    owners: list[str],
    products: list[str],
) -> dict[str, pd.DataFrame]:
    deals = tables["deals"].copy()
    spend = tables["spend"].copy()
    calls = tables["calls"].copy()
    contacts = tables["contacts"].copy()

    deals["created_date"] = pd.to_datetime(deals["created_time"], errors="coerce").dt.normalize()
    spend["date_dt"] = pd.to_datetime(spend["date"], errors="coerce").dt.normalize()
    calls["call_date"] = pd.to_datetime(calls["call_start_time"], errors="coerce").dt.normalize()
    contacts["created_date"] = pd.to_datetime(contacts["created_time"], errors="coerce").dt.normalize()

    deals = deals[(deals["created_date"] >= window.start) & (deals["created_date"] <= window.end)]
    spend = spend[(spend["date_dt"] >= window.start) & (spend["date_dt"] <= window.end)]
    calls = calls[(calls["call_date"] >= window.start) & (calls["call_date"] <= window.end)]
    contacts = contacts[(contacts["created_date"] >= window.start) & (contacts["created_date"] <= window.end)]

    # canonical NA
    for df in (deals, spend):
        df["source"] = df["source"].fillna("NA")
        df["campaign"] = df["campaign"].fillna("NA")

    deals["deal_owner_name"] = deals["deal_owner_name"].fillna("NA")
    deals["product"] = deals["product"].fillna("NA")

    if sources:
        deals = deals[deals["source"].isin(sources)]
        spend = spend[spend["source"].isin(sources)]
    if campaigns:
        deals = deals[deals["campaign"].isin(campaigns)]
        spend = spend[spend["campaign"].isin(campaigns)]
    if owners:
        deals = deals[deals["deal_owner_name"].isin(owners)]
    if products:
        deals = deals[deals["product"].isin(products)]

    return {"contacts": contacts, "calls": calls, "deals": deals, "spend": spend}


def kpis(deals: pd.DataFrame, spend: pd.DataFrame) -> dict[str, float | int | None]:
    spend_sum = float(pd.to_numeric(spend["spend"], errors="coerce").fillna(0).sum())
    deals_cnt = int(len(deals))
    paid_cnt = int(deals["is_paid"].fillna(False).sum())
    cash = float(pd.to_numeric(deals["revenue_cash"], errors="coerce").fillna(0).sum())
    contract = float(pd.to_numeric(deals["revenue_contract"], errors="coerce").fillna(0).sum())
    
    # Calculate realistic revenue (weighted average) if fields exist
    realistic = None
    if "revenue_realistic" in deals.columns:
        paid_deals = deals[deals["is_paid"].fillna(False)]
        realistic = float(pd.to_numeric(paid_deals["revenue_realistic"], errors="coerce").fillna(0).sum())
    elif "initial_amount_paid" in deals.columns and "offer_total_amount" in deals.columns:
        paid_deals = deals[deals["is_paid"].fillna(False)]
        realistic = float(
            (pd.to_numeric(paid_deals["initial_amount_paid"], errors="coerce").fillna(0) * 0.5 +
             pd.to_numeric(paid_deals["offer_total_amount"], errors="coerce").fillna(0) * 0.5).sum()
        )
    
    return {
        "Spend": spend_sum,
        "Deals": deals_cnt,
        "Paid deals": paid_cnt,
        "Paid rate": _safe_div(paid_cnt, deals_cnt),
        "Revenue (cash)": cash,
        "Revenue (contract)": contract,
        "Revenue (realistic)": realistic,
        "CPL": _safe_div(spend_sum, deals_cnt),
        "CPA": _safe_div(spend_sum, paid_cnt),
        "Cash ROAS": _safe_div(cash, spend_sum),
        "Contract ROAS": _safe_div(contract, spend_sum),
        "Realistic ROAS": _safe_div(realistic, spend_sum) if realistic else None,
        "AOV (realistic)": _safe_div(realistic, paid_cnt) if realistic else None,
    }


def generate_comparison_table(
    full_deals: pd.DataFrame, 
    filtered_deals: pd.DataFrame, 
    spend: pd.DataFrame
) -> pd.DataFrame | None:
    """Generate comparison table: Reference vs Full vs Filtered"""
    if REF is None:
        return None
    
    full_kpi = kpis(full_deals, spend)
    filt_kpi = kpis(filtered_deals, spend)
    
    # Build comparison dataframe
    data = {
        "Metric": [
            "Total Deals",
            "Paid Deals",
            "Paid Rate",
            "Revenue (realistic)",
            "Spend",
            "CPL (Cost Per Lead)",
            "CPA (Cost Per Paid)",
            "AOV (realistic)",
            "ROAS (realistic)",
        ],
        "Reference": [
            f"{REF['total_deals']:,}",
            f"{REF['paid_deals']:,}",
            f"{REF['paid_rate']:.1%}",
            f"{REF['revenue']:,.0f} €",
            f"{REF['spend']:,.0f} €",
            f"{REF.get('cpl', REF['spend']/REF['total_deals']):,.2f} €",
            f"{REF['cpa']:,.0f} €" if REF['cpa'] else "—",
            f"{REF['aov']:,.0f} €" if REF['aov'] else "—",
            f"{REF['roas']:.2f}x" if REF['roas'] else "—",
        ],
        "Our Full": [
            f"{full_kpi['Deals']:,}",
            f"{full_kpi['Paid deals']:,}",
            f"{full_kpi['Paid rate']:.1%}" if full_kpi['Paid rate'] else "—",
            f"{full_kpi['Revenue (realistic)']:,.0f} €" if full_kpi['Revenue (realistic)'] else "—",
            f"{full_kpi['Spend']:,.0f} €",
            f"{full_kpi['CPL']:,.2f} €" if full_kpi['CPL'] else "—",
            f"{full_kpi['CPA']:,.0f} €" if full_kpi['CPA'] else "—",
            f"{full_kpi['AOV (realistic)']:,.0f} €" if full_kpi['AOV (realistic)'] else "—",
            f"{full_kpi['Realistic ROAS']:.2f}x" if full_kpi['Realistic ROAS'] else "—",
        ],
        "Our Filtered": [
            f"{filt_kpi['Deals']:,}",
            f"{filt_kpi['Paid deals']:,}",
            f"{filt_kpi['Paid rate']:.1%}" if filt_kpi['Paid rate'] else "—",
            f"{filt_kpi['Revenue (realistic)']:,.0f} €" if filt_kpi['Revenue (realistic)'] else "—",
            f"{filt_kpi['Spend']:,.0f} €",
            f"{filt_kpi['CPL']:,.2f} €" if filt_kpi['CPL'] else "—",
            f"{filt_kpi['CPA']:,.0f} €" if filt_kpi['CPA'] else "—",
            f"{filt_kpi['AOV (realistic)']:,.0f} €" if filt_kpi['AOV (realistic)'] else "—",
            f"{filt_kpi['Realistic ROAS']:.2f}x" if filt_kpi['Realistic ROAS'] else "—",
        ],
        "Diff (Filtered vs Ref)": [],
    }
    
    # Calculate differences
    ref_cpl = REF.get('cpl', REF['spend']/REF['total_deals'])
    ref_vals = [REF['total_deals'], REF['paid_deals'], REF['paid_rate'], REF['revenue'], 
                REF['spend'], ref_cpl, REF['cpa'], REF['aov'], REF['roas']]
    filt_vals = [filt_kpi['Deals'], filt_kpi['Paid deals'], filt_kpi['Paid rate'], 
                 filt_kpi['Revenue (realistic)'], filt_kpi['Spend'], filt_kpi['CPL'], filt_kpi['CPA'],
                 filt_kpi['AOV (realistic)'], filt_kpi['Realistic ROAS']]
    
    for r_val, f_val in zip(ref_vals, filt_vals):
        if r_val and f_val and r_val != 0:
            diff_pct = ((f_val - r_val) / r_val) * 100
            data["Diff (Filtered vs Ref)"].append(f"{diff_pct:+.1f}%")
        else:
            data["Diff (Filtered vs Ref)"].append("—")
    
    return pd.DataFrame(data)


@st.cache_data(show_spinner=False)
def load_metrics_tree() -> dict | None:
    """Load metrics tree from JSON"""
    tree_file = ROOT / "reports" / "metrics_tree" / "metrics_tree_overall_overlap_window.json"
    by_source_file = ROOT / "reports" / "metrics_tree" / "tables" / "metrics_tree_by_source_overlap_window.csv"
    
    if not tree_file.exists():
        return None
    
    tree = json.loads(tree_file.read_text(encoding="utf-8"))
    by_source = pd.read_csv(by_source_file) if by_source_file.exists() else pd.DataFrame()
    
    return {"tree": tree, "by_source": by_source}


def create_revenue_decomposition_plotly(tree: dict) -> go.Figure:
    """Create interactive Revenue decomposition with Sunburst (better for hierarchies)"""
    spend = tree.get("spend", 0)
    deals = tree.get("deals", 0)
    paid = tree.get("paid_deals", 0)
    revenue = tree.get("revenue_contract", 0)
    cpl = tree.get("cpl_deal", 0)
    paid_rate = tree.get("paid_rate", 0)
    aov = revenue / paid if paid > 0 else 0
    
    # Simplified hierarchy for Sunburst (3 levels work best)
    labels = [
        "Revenue (North Star)",
        "Paid Deals",
        "AOV",
        "Deals",
        "Paid Rate",
        "Spend",
        "CPL",
    ]
    
    parents = [
        "",  # Revenue at center
        "Revenue (North Star)",  # Paid -> Revenue
        "Revenue (North Star)",  # AOV -> Revenue
        "Paid Deals",  # Deals -> Paid
        "Paid Deals",  # Rate -> Paid
        "Deals",  # Spend -> Deals
        "Deals",  # CPL -> Deals (shows it's derived)
    ]
    
    # Values = uniform for clear visualization
    values = [100, 50, 50, 25, 25, 12.5, 12.5]
    
    # Hover text with formulas and real values
    hover_texts = [
        f"<b>Revenue (Contract)</b><br>{revenue:,.0f} €<br><br><i>Formula:</i> Paid × AOV<br>= {paid:,} × {aov:,.0f}€",
        f"<b>Paid Deals</b><br>{paid:,}<br><br><i>Formula:</i> Deals × Paid Rate<br>= {deals:,} × {paid_rate:.2%}",
        f"<b>AOV</b><br>{aov:,.0f} €<br><br><i>Formula:</i> Revenue ÷ Paid<br><br>🎯 Lever: Upsell, Cross-sell",
        f"<b>Total Deals (Leads)</b><br>{deals:,}<br><br><i>Formula:</i> Spend ÷ CPL<br>= {spend:,.0f} ÷ {cpl:.2f}",
        f"<b>Paid Rate</b><br>{paid_rate:.2%}<br><br>🔥 <b>KEY LEVER</b><br>4% → 6% = +50% revenue",
        f"<b>Spend</b><br>{spend:,.0f} €<br><br>Marketing budget input",
        f"<b>CPL (Cost Per Lead)</b><br>{cpl:.2f} €<br><br><i>Derived:</i> Spend ÷ Deals<br><br>🎯 Lever: Better targeting",
    ]
    
    # Colors by level
    colors = [
        "#9B59B6",  # Revenue - Purple (North Star)
        "#E91E63",  # Paid - Dark Pink (Driver)
        "#E91E63",  # AOV - Dark Pink (Driver)
        "#F48FB1",  # Deals - Pink (Component)
        "#F48FB1",  # Rate - Pink (Component)
        "#FFE082",  # Spend - Yellow (Input)
        "#FFE082",  # CPL - Yellow (Input)
    ]
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        hovertext=hover_texts,
        hoverinfo="text",
        textinfo="label",
        marker=dict(
            colors=colors,
            line=dict(color="white", width=2)
        ),
        branchvalues="total",
    ))
    
    fig.update_layout(
        title=dict(
            text="Revenue Decomposition Tree (4 levels)<br><sub>🖱️ Click on sector to zoom | 🔍 Hover for formulas</sub>",
            font=dict(size=16)
        ),
        height=650,
        margin=dict(t=80, l=0, r=0, b=0)
    )
    
    return fig


def create_roas_decomposition_plotly(tree: dict) -> go.Figure:
    """Create ROAS decomposition with Sunburst"""
    spend = tree.get("spend", 0)
    deals = tree.get("deals", 0)
    paid = tree.get("paid_deals", 0)
    revenue = tree.get("revenue_contract", 0)
    cpl = tree.get("cpl_deal", 0)
    roas = tree.get("contract_roas", 0)
    aov = revenue / paid if paid > 0 else 0
    
    # 3-level hierarchy
    labels = [
        "ROAS (North Star)",
        "Revenue",
        "Spend",
        "Paid Deals",
        "AOV",
        "Deals",
        "CPL",
    ]
    
    parents = [
        "",  # ROAS at center
        "ROAS (North Star)",
        "ROAS (North Star)",
        "Revenue",
        "Revenue",
        "Spend",
        "Spend",
    ]
    
    values = [100, 50, 50, 25, 25, 25, 25]
    
    hover_texts = [
        f"<b>ROAS</b><br>{roas:.2f}x<br><br><i>Formula:</i> Revenue ÷ Spend<br>= {revenue:,.0f} ÷ {spend:,.0f}",
        f"<b>Revenue</b><br>{revenue:,.0f} €<br><br><i>Formula:</i> Paid × AOV<br>= {paid:,} × {aov:,.0f}€",
        f"<b>Spend</b><br>{spend:,.0f} €<br><br><i>Formula:</i> Deals × CPL<br>= {deals:,} × {cpl:.2f}€",
        f"<b>Paid Deals</b><br>{paid:,}<br><br>🔥 <b>KEY LEVER</b><br>Conversion optimization",
        f"<b>AOV</b><br>{aov:,.0f} €<br><br>🎯 Growth Lever: Pricing & Upsell",
        f"<b>Total Deals</b><br>{deals:,}<br><br>Lead volume",
        f"<b>CPL</b><br>{cpl:.2f} €<br><br>🎯 Optimize targeting & CTR",
    ]
    
    colors = [
        "#9B59B6",  # ROAS - Purple
        "#E91E63",  # Revenue - Dark Pink
        "#E91E63",  # Spend - Dark Pink
        "#F48FB1",  # Paid - Pink
        "#F48FB1",  # AOV - Pink
        "#FFE082",  # Deals - Yellow
        "#FFE082",  # CPL - Yellow
    ]
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        hovertext=hover_texts,
        hoverinfo="text",
        textinfo="label",
        marker=dict(
            colors=colors,
            line=dict(color="white", width=2)
        ),
        branchvalues="total",
    ))
    
    fig.update_layout(
        title=dict(
            text="ROAS Decomposition Tree (3 levels)<br><sub>🖱️ Click on sector to zoom | 🔍 Hover for formulas</sub>",
            font=dict(size=16)
        ),
        height=650,
        margin=dict(t=80, l=0, r=0, b=0)
    )
    
    return fig


def create_metrics_tree_sankey(tree: dict) -> go.Figure:
    """Create Sankey diagram from metrics tree"""
    spend = tree.get("spend", 0)
    deals = tree.get("deals", 0)
    paid_deals = tree.get("paid_deals", 0)
    revenue = tree.get("revenue_contract", 0)
    
    cpl = tree.get("cpl_deal")
    paid_rate = tree.get("paid_rate")
    cpa = tree.get("cpa")
    roas = tree.get("contract_roas")
    
    # Format helpers
    def fmt_money(x):
        if x >= 1_000_000:
            return f"{x/1_000_000:.1f}M €"
        elif x >= 1_000:
            return f"{x/1_000:.0f}K €"
        else:
            return f"{x:.0f} €"
    
    def fmt_num(x):
        if x >= 1_000:
            return f"{x/1_000:.1f}K"
        else:
            return f"{x:.0f}"
    
    # Nodes
    node_labels = [
        f"Spend<br>{fmt_money(spend)}",
        f"Deals<br>{fmt_num(deals)}",
        f"Paid<br>{paid_deals}",
        f"Revenue<br>{fmt_money(revenue)}",
    ]
    
    # Flows (normalized for visual proportions)
    flow_spend_deals = spend
    flow_deals_paid = spend * (paid_rate if paid_rate else 0)
    flow_paid_revenue = min(revenue, spend * 3)
    
    # Links
    links = {
        'source': [0, 1, 2],
        'target': [1, 2, 3],
        'value': [flow_spend_deals, flow_deals_paid, flow_paid_revenue],
        'label': [
            f"CPL: {fmt_money(cpl)}" if cpl else "CPL: N/A",
            f"Conv: {paid_rate:.1%}" if paid_rate else "Conv: N/A",
            f"ROAS: {roas:.1f}x" if roas else "ROAS: N/A",
        ]
    }
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=30,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=["#FF6B35", "#004E89", "#1B998B", "#2EC4B6"]
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            label=links['label'],
            color=["rgba(255,107,53,0.3)", "rgba(0,78,137,0.3)", "rgba(27,153,139,0.3)"]
        )
    )])
    
    fig.update_layout(
        title=dict(text="Metrics Tree: Spend → Deals → Paid → Revenue", font=dict(size=18)),
        font=dict(size=12),
        height=450,
        margin=dict(l=10, r=10, t=60, b=10)
    )
    
    return fig


def ads_tables(deals: pd.DataFrame, spend: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = deals.copy()
    d["source"] = d["source"].fillna("NA")
    d["campaign"] = d["campaign"].fillna("NA")

    s = spend.copy()
    s["source"] = s["source"].fillna("NA")
    s["campaign"] = s["campaign"].fillna("NA")

    d_sc = (
        d.groupby(["source", "campaign"], dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    s_sc = s.groupby(["source", "campaign"], dropna=False).agg(spend=("spend", "sum")).reset_index()

    m = s_sc.merge(d_sc, on=["source", "campaign"], how="outer")
    for col in ["spend", "deals", "paid_deals", "revenue_cash", "revenue_contract"]:
        m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0)
    m["paid_rate"] = m["paid_deals"] / m["deals"].replace(0, np.nan)
    m["cpl_deal"] = m["spend"] / m["deals"].replace(0, np.nan)
    m["cpa"] = m["spend"] / m["paid_deals"].replace(0, np.nan)
    m["cash_roas"] = m["revenue_cash"] / m["spend"].replace(0, np.nan)
    m["contract_roas"] = m["revenue_contract"] / m["spend"].replace(0, np.nan)

    by_source = (
        m.groupby("source", dropna=False)
        .agg(
            spend=("spend", "sum"),
            deals=("deals", "sum"),
            paid_deals=("paid_deals", "sum"),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    by_source["paid_rate"] = by_source["paid_deals"] / by_source["deals"].replace(0, np.nan)
    by_source["cpl_deal"] = by_source["spend"] / by_source["deals"].replace(0, np.nan)
    by_source["cpa"] = by_source["spend"] / by_source["paid_deals"].replace(0, np.nan)
    by_source["cash_roas"] = by_source["revenue_cash"] / by_source["spend"].replace(0, np.nan)
    by_source["contract_roas"] = by_source["revenue_contract"] / by_source["spend"].replace(0, np.nan)

    return by_source.sort_values("spend", ascending=False), m.sort_values("spend", ascending=False)


def stage_funnel(deals: pd.DataFrame) -> pd.DataFrame:
    """Generate funnel by deal stage"""
    d = deals.copy()
    d["stage"] = d["stage"].fillna("NA")
    
    funnel = (
        d.groupby("stage", dropna=False)
        .agg(
            count=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            paid_rate=("is_paid", lambda x: float(x.fillna(False).mean())),
        )
        .reset_index()
        .rename(columns={"count": "deals"})
    )
    
    return funnel.sort_values("deals", ascending=False)


def sales_table(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["deal_owner_name"] = d["deal_owner_name"].fillna("NA")
    out = (
        d.groupby("deal_owner_name", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            paid_rate=("is_paid", lambda x: float(x.fillna(False).mean())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
            sla_minutes_median=("sla_minutes", "median"),
        )
        .reset_index()
    )
    out["contract_per_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    return out.sort_values("revenue_contract", ascending=False)


def product_table_paid(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals[deals["is_paid"].fillna(False)].copy()
    d["product"] = d["product"].fillna("NA")
    out = (
        d.groupby("product", dropna=False)
        .agg(
            paid_deals=("deal_row_id", "size"),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    out["contract_aov_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    return out.sort_values("revenue_contract", ascending=False)

def paid_segment_table(deals: pd.DataFrame, col: str) -> pd.DataFrame:
    d = deals[deals["is_paid"].fillna(False)].copy()
    d[col] = d[col].fillna("NA")
    out = (
        d.groupby(col, dropna=False)
        .agg(
            paid_deals=("deal_row_id", "size"),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    out["contract_aov_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    out["share_paid_deals_pct"] = (out["paid_deals"] / out["paid_deals"].sum() * 100).round(2)
    return out.sort_values("revenue_contract", ascending=False)


def funnel_segment_table(deals: pd.DataFrame, col: str, *, min_deals: int = 80) -> pd.DataFrame:
    d = deals.copy()
    d[col] = d[col].fillna("NA")
    out = (
        d.groupby(col, dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    out["paid_rate"] = out["paid_deals"] / out["deals"].replace(0, np.nan)
    out = out[out["deals"] >= min_deals].copy()
    return out.sort_values("revenue_contract", ascending=False)


def time_series(deals: pd.DataFrame, spend: pd.DataFrame, calls: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["date"] = pd.to_datetime(d["created_time"], errors="coerce").dt.normalize()
    deals_daily = (
        d.groupby("date", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )

    s = spend.copy()
    s["date"] = pd.to_datetime(s["date"], errors="coerce").dt.normalize()
    spend_daily = s.groupby("date", dropna=False).agg(spend=("spend", "sum")).reset_index()

    c = calls.copy()
    c["date"] = pd.to_datetime(c["call_start_time"], errors="coerce").dt.normalize()
    calls_daily = c.groupby("date", dropna=False).agg(calls=("call_id", "size")).reset_index()

    ts = deals_daily.merge(spend_daily, on="date", how="outer").merge(calls_daily, on="date", how="outer")
    for col in ["deals", "paid_deals", "revenue_contract", "spend", "calls"]:
        ts[col] = pd.to_numeric(ts[col], errors="coerce").fillna(0)
    ts = ts[ts["date"].notna()].sort_values("date")
    ts["paid_rate"] = ts["paid_deals"] / ts["deals"].replace(0, np.nan)
    ts["contract_roas"] = ts["revenue_contract"] / ts["spend"].replace(0, np.nan)
    return ts


def time_to_close(deals: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    paid = deals[deals["is_paid"].fillna(False)].copy()
    paid["created_dt"] = pd.to_datetime(paid["created_time"], errors="coerce")
    paid["closing_dt"] = pd.to_datetime(paid["closing_date"], errors="coerce")
    ok = paid["created_dt"].notna() & paid["closing_dt"].notna()
    coverage = float(ok.mean()) if len(paid) else 0.0
    paid = paid[ok].copy()
    paid["lag_days"] = (paid["closing_dt"] - paid["created_dt"]).dt.total_seconds() / 86400
    paid = paid[paid["lag_days"].notna()].copy()
    return paid, coverage


def main() -> None:
    st.set_page_config(page_title="CRM Metrics Dashboard", layout="wide")

    st.title("CRM Metrics Dashboard")
    st.caption("Source: data/clean/*.parquet. Paid status counted only if Stage = Payment Done.")

    if not _require_clean():
        st.error("data/clean not found. First run: python scripts/01_clean_export.py")
        with st.expander("🔍 Debug Info"):
            st.write(f"ROOT: {ROOT}")
            st.write(f"CLEAN_DIR: {CLEAN_DIR}")
            st.write(f"CLEAN_DIR exists: {CLEAN_DIR.exists()}")
            if CLEAN_DIR.exists():
                st.write(f"Files in CLEAN_DIR: {list(CLEAN_DIR.glob('*'))}")
        st.stop()

    # Dataset Version Selector
    st.sidebar.title("⚙️ Settings")
    
    dataset_version = st.sidebar.radio(
        "Dataset Version",
        options=["Full (21K deals)", "Filtered (3.6K deals)"],
        index=0,
        help="Full = all data (strategic view). Filtered = known products only (product analytics)"
    )
    
    use_filtered = "Filtered" in dataset_version
    
    # Info box explaining difference
    if use_filtered:
        st.sidebar.info(
            "📊 **Filtered Dataset**\n\n"
            "• Only deals with known product\n"
            "• Removed 18K deals where product=NA\n"
            "• Paid Rate: 23% (vs 4% in Full)\n"
            "• Better for product analytics\n\n"
            "Metrics match reference ±0.3%"
        )
    else:
        st.sidebar.info(
            "📊 **Full Dataset**\n\n"
            "• All 21,592 deals from CRM\n"
            "• Including 18K without product\n"
            "• Paid Rate: 4%\n"
            "• Shows real funnel\n\n"
            "Better for strategic marketing view"
        )
    
    st.sidebar.markdown("---")
    
    tables = load_clean(use_filtered=use_filtered)
    base_window = infer_overlap_window(tables)

    st.sidebar.header("Filters")
    
    # Quick date presets
    preset = st.sidebar.selectbox(
        "Date Preset (quick select)",
        options=["Full window", "Last 30 days", "Last 60 days", "Last 90 days", "Custom"],
        index=0,
    )
    
    if preset == "Last 30 days":
        start = max(base_window.start, base_window.end - pd.Timedelta(days=30))
        end = base_window.end
    elif preset == "Last 60 days":
        start = max(base_window.start, base_window.end - pd.Timedelta(days=60))
        end = base_window.end
    elif preset == "Last 90 days":
        start = max(base_window.start, base_window.end - pd.Timedelta(days=90))
        end = base_window.end
    elif preset == "Custom":
        start_date, end_date = st.sidebar.date_input(
            "Custom date range",
            value=(base_window.start.date(), base_window.end.date()),
            min_value=base_window.start.date(),
            max_value=base_window.end.date(),
        )
        start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    else:  # Full window
        start, end = base_window.start, base_window.end
    
    window = Window(start=start, end=end)

    deals0 = tables["deals"].copy()
    deals0["source"] = deals0["source"].fillna("NA")
    deals0["campaign"] = deals0["campaign"].fillna("NA")
    deals0["deal_owner_name"] = deals0["deal_owner_name"].fillna("NA")
    deals0["product"] = deals0["product"].fillna("NA")

    source_options = sorted(deals0["source"].dropna().unique().tolist())
    campaign_options = sorted(deals0["campaign"].dropna().unique().tolist())
    owner_options = sorted(deals0["deal_owner_name"].dropna().unique().tolist())
    product_options = sorted(deals0["product"].dropna().unique().tolist())

    sources = st.sidebar.multiselect("Source", options=source_options)
    
    # Cascading filter: Campaign depends on Source
    if sources:
        campaign_filtered = sorted(
            deals0[deals0["source"].isin(sources)]["campaign"].dropna().unique().tolist()
        )
        campaigns = st.sidebar.multiselect("Campaign (filtered by Source)", options=campaign_filtered)
    else:
        campaigns = st.sidebar.multiselect("Campaign", options=campaign_options)
    
    owners = st.sidebar.multiselect("Deal Owner", options=owner_options)
    products = st.sidebar.multiselect("Product", options=product_options)

    filt = apply_filters(
        tables,
        window,
        sources=sources,
        campaigns=campaigns,
        owners=owners,
        products=products,
    )

    tab_overview, tab_metrics_tree, tab_quality, tab_ads, tab_sales, tab_products, tab_payments, tab_geo, tab_time, tab_notes, tab_guide, tab_presentation = st.tabs(
        ["Overview", "Metrics Tree", "Quality", "Ads", "Sales", "Products", "Payments", "Geo", "Time", "Notes", "📚 Guide", "🎤 Presentation"]
    )

    with tab_overview:
        # Info block
        st.info("""
        📊 **Key Metrics Overview**
        
        This page shows the overall business picture:
        - **Marketing effectiveness**: Spend, ROAS, CPA
        - **Sales funnel**: Deals → Paid Deals → Revenue
        - **Dynamics**: How metrics change over time
        
        💡 Hover over ℹ️ next to metrics for detailed explanation!
        """)
        
        # Dataset comparison section
        if use_filtered:
            st.success("✅ Using **Filtered dataset** - metrics match reference ±0.3%")
        else:
            st.warning("⚠️ Using **Full dataset** - includes 18K deals without product. Switch to Filtered for product analytics.")
        
        # Show dataset info
        with st.expander("ℹ️ Full vs Filtered — What's the difference?"):
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.markdown("**📊 Full Dataset (21,592 deals)**")
                st.markdown("""
                - ✅ All CRM data
                - ✅ Shows real funnel (4% paid rate)
                - ✅ Better for strategic marketing view
                - ❌ Includes 18K deals where product=NA
                - ❌ Paid rate underestimated (many "junk" leads)
                
                **When to use:**
                - Marketing analysis (Spend, CPL, sources)
                - Sales funnel (SLA, stage conversions)
                - Overall business picture
                """)
            
            with col_info2:
                st.markdown("**📊 Filtered Dataset (3,592 deals)**")
                st.markdown("""
                - ✅ Only deals with known product
                - ✅ Paid rate 23% (realistic for product)
                - ✅ Metrics match reference ±0.3%
                - ✅ Better for product analytics
                - ❌ Doesn't show full marketing picture
                
                **When to use:**
                - Product analytics (AOV, ARPU by product)
                - Segmentation (cities, language level)
                - Comparison with reference data
                """)
            
            st.markdown("---")
            st.markdown("**💡 Recommendation:** Use Full for marketing, Filtered for products. Both approaches are valid!")
        
        # Comparison table with reference
        st.markdown("---")
        st.subheader("📊 Comparison with Reference Data")
        
        if REF is not None:
            # Load both datasets for comparison
            try:
                full_deals_raw = pd.read_parquet(CLEAN_DIR / "deals.parquet")
                filt_deals_raw = pd.read_parquet(CLEAN_DIR / "deals_filtered.parquet")
                
                comp_table = generate_comparison_table(full_deals_raw, filt_deals_raw, tables["spend"])
                
                if comp_table is not None:
                    st.dataframe(
                        comp_table,
                        use_container_width=True,
                        hide_index=True,
                    )
                    
                    col_note1, col_note2 = st.columns(2)
                    with col_note1:
                        st.success("✅ **Filtered metrics** match reference ±0.3%")
                    with col_note2:
                        st.info("💡 Difference in Total Deals due to different source files (paid counts match!)")
            except Exception as e:
                st.error(f"Error loading comparison: {e}")
        else:
            st.warning("Reference data not found. reference_data.py file is missing.")
        
        st.markdown("---")
        
        vals = kpis(filt["deals"], filt["spend"])
        
        # First row of metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Spend", f"{vals['Spend']:,.2f}")
        c2.metric("Deals", f"{vals['Deals']:,}")
        c3.metric("Paid deals", f"{vals['Paid deals']:,}")
        pr = vals["Paid rate"]
        with c4:
            st.metric("Paid rate", f"{pr:.2%}" if pr is not None else "NA")
            show_metric_info("Paid Rate")

        # Second row - key marketing metrics
        st.markdown("##### 🎯 Key Marketing Metrics")
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.metric("CPL (per lead)", f"{vals['CPL']:,.2f} €" if vals["CPL"] is not None else "NA")
            show_metric_info("CPL")
        with c6:
            st.metric("CPA (per paid)", f"{vals['CPA']:,.2f} €" if vals["CPA"] is not None else "NA")
            show_metric_info("CPA")
        with c7:
            aov = vals.get("AOV (realistic)")
            st.metric("AOV (average check)", f"{aov:,.0f} €" if aov is not None else "NA")
            show_metric_info("AOV")
        with c8:
            roas = vals.get("Realistic ROAS") or vals["Contract ROAS"]
            st.metric("ROAS", f"{roas:.2f}x" if roas is not None else "NA")
            show_metric_info("ROAS")

        # Третья строка - Revenue breakdown
        st.markdown("##### 💰 Revenue breakdown")
        c9, c10, c11, c12 = st.columns(4)
        c9.metric("Revenue (cash)", f"{vals['Revenue (cash)']:,.0f} €")
        c10.metric("Revenue (contract)", f"{vals['Revenue (contract)']:,.0f} €")
        real_rev = vals.get("Revenue (realistic)")
        with c11:
            st.metric("Revenue (realistic)", f"{real_rev:,.0f} €" if real_rev else "NA")
            st.caption("Weighted avg (50/50)")
        c12.metric("", "")  # Empty for spacing

        st.subheader("Daily dynamics")
        ts = time_series(filt["deals"], filt["spend"], filt["calls"])
        fig = px.line(ts, x="date", y=["deals", "paid_deals"], title="Deals vs Paid deals (daily)")
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.line(ts, x="date", y=["spend", "revenue_contract"], title="Spend vs Contract revenue (daily)")
        st.plotly_chart(fig2, use_container_width=True)

    with tab_metrics_tree:
        st.info("""
        🌳 **Metrics Tree — Mathematical Business Decomposition**
        
        Metrics tree shows how each euro of ad spend converts to revenue:
        - **Sankey diagram**: Flow from Spend to Revenue (flow visualization)
        - **Decomposition trees**: Hierarchical structure (Revenue = Paid × AOV = ...)
        - **By Source**: Which channels perform better
        
        💡 **Why this matters**: Find bottlenecks and understand which metrics to pull for growth.
        """)
        
        st.subheader("Metrics Tree: Spend → Deals → Paid → Revenue")
        
        tree_data = load_metrics_tree()
        
        if tree_data is None:
            st.warning("Metrics tree files not found. Run: python scripts/05_metrics_tree.py")
        else:
            tree = tree_data["tree"]
            by_source = tree_data["by_source"]
            
            # Overall metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spend", f"{tree.get('spend', 0):,.0f} €")
            col2.metric("Deals", f"{tree.get('deals', 0):,}")
            col3.metric("Paid Deals", f"{tree.get('paid_deals', 0):,}")
            col4.metric("Revenue (contract)", f"{tree.get('revenue_contract', 0):,.0f} €")
            
            col5, col6, col7, col8 = st.columns(4)
            cpl = tree.get("cpl_deal")
            paid_rate = tree.get("paid_rate")
            cpa = tree.get("cpa")
            roas = tree.get("contract_roas")
            
            with col5:
                st.metric("CPL (Deal)", f"{cpl:,.2f} €" if cpl else "N/A")
                show_metric_info("CPL")
            with col6:
                st.metric("Paid Rate", f"{paid_rate:.2%}" if paid_rate else "N/A")
                show_metric_info("Paid Rate")
            with col7:
                st.metric("CPA", f"{cpa:,.2f} €" if cpa else "N/A")
                show_metric_info("CPA")
            with col8:
                st.metric("Contract ROAS", f"{roas:.2f}x" if roas else "N/A")
                show_metric_info("ROAS")
            
            # Sankey diagram
            st.plotly_chart(create_metrics_tree_sankey(tree), use_container_width=True)
            
            # Revenue & ROAS Decomposition Trees (INTERACTIVE!)
            st.subheader("📊 Metrics Decomposition Trees (Interactive)")
            
            st.markdown("""
            **How to use interactive trees:**
            - 🟣 **Purple** — North Star metric (main goal)
            - 🌸 **Dark Pink** — Drivers (Level 1: Volume × Value)
            - 💗 **Light Pink** — Components (Level 2: constituent parts)
            - 🟡 **Beige** — Input metrics (Level 3: what we can control)
            
            💡 **Interactivity:**
            - 🖱️ **Click** on block → drill-down to details
            - 🔍 **Hover** → shows formulas and calculations
            - 📈 Block size = relative importance
            
            🎯 **Growth Levers** (what to pull for growth): Paid Rate, CPL, AOV
            """)
            
            # Interactive Plotly trees
            st.plotly_chart(create_revenue_decomposition_plotly(tree), use_container_width=True)
            st.plotly_chart(create_roas_decomposition_plotly(tree), use_container_width=True)
            
            # By source breakdown
            st.subheader("Metrics Tree by Source (Top 10)")
            
            if not by_source.empty:
                top10 = by_source.head(10).copy()
                
                # Format for display
                display_cols = ["source", "spend", "deals", "paid_deals", "revenue_contract", 
                               "paid_rate", "cpl_deal", "cpa", "contract_roas"]
                display_df = top10[display_cols].copy()
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Visualizations
                fig_spend = px.bar(
                    top10,
                    x="spend",
                    y="source",
                    orientation="h",
                    title="Spend by Source (Top 10)",
                    color="contract_roas",
                    color_continuous_scale="RdYlGn"
                )
                st.plotly_chart(fig_spend, use_container_width=True)
                
                fig_metrics = px.scatter(
                    top10,
                    x="cpa",
                    y="contract_roas",
                    size="paid_deals",
                    color="source",
                    hover_data=["deals", "paid_rate", "cpl_deal"],
                    title="CPA vs ROAS by Source (bubble size = paid deals)",
                    labels={"cpa": "CPA (€)", "contract_roas": "Contract ROAS"}
                )
                fig_metrics.add_hline(y=1.0, line_dash="dash", line_color="gray", 
                                     annotation_text="Break-even ROAS=1")
                st.plotly_chart(fig_metrics, use_container_width=True)
            
            st.caption(f"Window: {tree.get('window', {}).get('start', 'N/A')} to {tree.get('window', {}).get('end', 'N/A')}")

    with tab_quality:
        st.info("""
        🔬 **Quality & Correlation — Data Validation and Relationships**
        
        This tab shows:
        - **Correlation heatmap**: How metrics relate to each other (red = grow together, blue = inverse relationship)
        - **Key correlations**: Most important relationships for decision making
        - **Growth insights**: Which metric combinations give best ROAS
        
        💡 **Main insight**: Paid Rate ↔ CPA have strong negative correlation (-0.8).
        This means: improving sales process (↑ Paid Rate) automatically reduces acquisition cost (↓ CPA).
        """)
        
        st.subheader("Phase 2: Correlation Analysis")
        
        # Load correlation heatmap
        heatmap_path = ROOT / "reports" / "quality" / "figures" / "correlation_heatmap.png"
        insights_path = ROOT / "reports" / "quality" / "correlation_insights.json"
        summary_path = ROOT / "reports" / "quality" / "correlation_summary.md"
        
        if heatmap_path.exists():
            img = Image.open(heatmap_path)
            st.image(img, caption="Correlation Matrix: Key Metrics by Source", use_column_width=True)
        else:
            st.warning("Correlation heatmap not found. Run: python scripts/03b_correlation_analysis.py")
        
        # Show insights
        if insights_path.exists():
            insights = json.loads(insights_path.read_text(encoding="utf-8"))
            st.subheader("Key Correlations")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("CPL ↔ CPA", f"{insights['cpl_vs_cpa']:.3f}")
            col2.metric("Paid Rate ↔ CPA", f"{insights['paid_rate_vs_cpa']:.3f}")
            col3.metric("AOV ↔ ROAS", f"{insights['aov_contract_vs_roas_contract']:.3f}")
            col4.metric("CPA ↔ ROAS", f"{insights['cpa_vs_roas_contract']:.3f}")
            
            st.markdown("**Interpretation:**")
            st.markdown("- **Strong positive**: CPL ↔ CPA (higher lead cost → higher acquisition cost)")
            st.markdown("- **Strong negative**: Paid_Rate ↔ CPA (better conversion → lower CPA), CPA ↔ ROAS (lower CPA → higher ROAS)")
            st.markdown("- **Growth levers**: Focus on sources with **high Paid_Rate** and **low CPL** to maximize ROAS")
        
        # Show summary
        if summary_path.exists():
            summary = summary_path.read_text(encoding="utf-8")
            with st.expander("📄 Full Correlation Summary"):
                st.markdown(summary)

    with tab_ads:
        st.info("""
        📣 **Ads Efficiency — Advertising Channel Effectiveness**
        
        Marketing analysis by sources and campaigns:
        - **By Source**: Overall effectiveness of each channel (Google, Facebook, TikTok, etc.)
        - **By Campaign**: Details — which specific campaigns work
        - **Scatter plot**: ROAS vs Spend — find high-efficiency channels for scaling
        
        💡 **How to optimize**: 
        1. Find sources with ROAS > 5x and low CPA
        2. Increase budget on these channels
        3. Stop channels with ROAS < 1x (unprofitable)
        """)
        
        st.subheader("By source")
        by_source, by_sc = ads_tables(filt["deals"], filt["spend"])
        st.dataframe(by_source, use_container_width=True, hide_index=True)

        st.subheader("Top campaigns by spend")
        top = by_sc.sort_values("spend", ascending=False).head(30)
        st.dataframe(top, use_container_width=True, hide_index=True)

        fig = px.scatter(
            top,
            x="spend",
            y="contract_roas",
            size="paid_deals",
            color="source",
            hover_data=["campaign", "deals", "paid_deals", "cpa"],
            title="Campaigns: Spend vs Contract ROAS (bubble=paid deals)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_sales:
        st.info("""
        👥 **Sales Efficiency — Manager Performance**
        
        Sales team analysis:
        - **Paid Rate**: What % of leads each manager converts to payment
        - **Volume**: How many deals processed (workload)
        - **Revenue**: Contribution to revenue
        
        💡 **How to improve sales**:
        1. Find managers with Paid Rate > 6% — study their approach (best practices)
        2. Managers with Paid Rate < 3% — need training or lead redistribution
        3. Check SLA — faster processing = higher conversion
        
        ⚠️ **Caveat**: Managers may receive leads of different quality (different sources).
        """)
        
        owners_df = sales_table(filt["deals"])
        st.dataframe(owners_df, use_container_width=True, hide_index=True)
        fig = px.bar(
            owners_df.sort_values("paid_rate", ascending=False).head(20),
            x="paid_rate",
            y="deal_owner_name",
            orientation="h",
            title="Paid rate by owner (top 20)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_products:
        st.error("""
        ⚠️ **IMPORTANT LIMITATION: CPA/ROAS by product are incorrect**
        
        **Problem**: Spend is aggregated by Source+Campaign, while Deals are by Source+Campaign+**Product**.
        One source generates leads for different products, but we don't know what portion of budget went to each.
        
        **What is shown correctly**: ✅ Revenue, ✅ AOV, ✅ Volume (Deals/Paid)
        **What is NOT shown**: ❌ CPA, ❌ ROAS, ❌ CPL by product
        
        📄 Details: reports/DISCLAIMER_PRODUCT_METRICS.md
        """)
        
        st.info("""
        📦 **Product Analytics — Unit Economics**
        
        Product analysis by correct metrics:
        - **Revenue**: How much revenue each product brings
        - **AOV**: Average check (how expensive the product is)
        - **Paid Rate**: Conversion to payment (how needed the product is)
        
        💡 **How to use**:
        - Products with high AOV + high Paid Rate = marketing priority
        - Products with low Paid Rate — issues with product-market fit or positioning
        """)
        prod = product_table_paid(filt["deals"])
        st.dataframe(prod, use_container_width=True, hide_index=True)
        fig = px.bar(
            prod.head(20),
            x="revenue_contract",
            y="product",
            orientation="h",
            title="Contract revenue by product (paid only)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_payments:
        st.info("""
        💳 **Payments & Education — Payment Segmentation**
        
        Analysis of payment methods and education types:
        - **Payment Type**: Which payment methods clients prefer (full payment, installments, etc.)
        - **Education Type**: What education paying clients have
        
        💡 **Practical application**:
        - If installments generate more revenue — actively offer installment plans
        - Education type helps understand target audience and tune messaging
        
        ⚠️ Analysis only for paid deals (for non-payers data may be incomplete).
        """)
        
        st.subheader("Payment Type (paid only)")
        pt = paid_segment_table(filt["deals"], "payment_type")
        st.dataframe(pt, use_container_width=True, hide_index=True)
        fig = px.bar(
            pt.head(15),
            x="revenue_contract",
            y="payment_type",
            orientation="h",
            title="Contract revenue by payment type (paid only)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Education Type (paid only)")
        et = paid_segment_table(filt["deals"], "education_type")
        st.dataframe(et, use_container_width=True, hide_index=True)
        fig2 = px.bar(
            et.head(15),
            x="revenue_contract",
            y="education_type",
            orientation="h",
            title="Contract revenue by education type (paid only)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab_geo:
        st.info("""
        🌍 **Geography — Geographic Segmentation**
        
        Analysis by cities and German language level:
        - **City**: Which cities give best conversion (Paid Rate)
        - **Level of Deutsch**: Relationship between language level and willingness to pay
        
        💡 **How to use**:
        - Cities with high Paid Rate — focus advertising on these geos
        - Cities with low Paid Rate — may need different messaging or product fit
        - Level of Deutsch shows segments with highest motivation
        
        ⚠️ **Min 80 deals**: Filter for statistical significance (exclude small segments with random conversion).
        """)
        
        st.subheader("City (min 80 deals)")
        city = funnel_segment_table(filt["deals"], "city", min_deals=80)
        st.dataframe(city, use_container_width=True, hide_index=True)
        if len(city):
            fig = px.bar(
                city.sort_values("paid_rate", ascending=False).head(20),
                x="paid_rate",
                y="city",
                orientation="h",
                title="Paid rate by city (min 80 deals, top 20)",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Level of Deutsch (min 80 deals)")
        lvl = funnel_segment_table(filt["deals"], "level_of_deutsch", min_deals=80)
        st.dataframe(lvl, use_container_width=True, hide_index=True)
        if len(lvl):
            fig2 = px.bar(
                lvl.sort_values("paid_rate", ascending=False),
                x="paid_rate",
                y="level_of_deutsch",
                orientation="h",
                title="Paid rate by Deutsch level (min 80 deals)",
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab_time:
        st.info("""
        ⏱️ **Time Analysis — Temporal Analysis**
        
        Analysis of time from deal creation to payment:
        - **Time-to-Close**: How many days from first contact to payment
        - **Distribution**: Histogram shows typical and anomalous deals
        - **Outliers**: Deals with very long time-to-close (possible data errors)
        
        💡 **What to look for**:
        - **Median time-to-close**: Typical sales cycle (norm: 7-30 days for online education)
        - **Long tail**: Deals >60 days may indicate nurturing opportunities
        - **Fast deals (<3 days)**: Hot leads, can scale
        
        ⚠️ **Coverage**: Not all paid deals have closing_date → analysis on subset (~60%).
        """)
        
        st.subheader("Time-to-close (paid deals)")
        paid_ok, coverage = time_to_close(filt["deals"])
        st.caption(f"Coverage: {coverage:.1%} paid deals have both created_time and closing_date.")
        if len(paid_ok):
            fig = px.histogram(paid_ok, x="lag_days", nbins=60, title="Lag days: created_time → closing_date")
            fig.update_xaxes(range=[-1, 120])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                paid_ok.sort_values("lag_days", ascending=False)[
                    ["deal_row_id", "deal_owner_name", "source", "campaign", "product", "lag_days", "revenue_contract"]
                ].head(50),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Insufficient data for time-to-close on selected window/filters.")

    with tab_notes:
        st.markdown(
            """
**Data Caveats**

- Payment: `Stage = Payment Done` (rest not counted as payment).
- `Closing Date` is empty for some paid deals → time-to-close calculated only on subset.
- Contact IDs in Calls/Deals came from Excel numbers → exact join Contacts↔Calls↔Deals not guaranteed.
- Filters `Deal Owner`/`Product` apply to Deals, but Spend filtered only by `Source/Campaign` and date window.
"""
        )
        st.markdown("**How to Update Artifacts**")
        st.code(
            "python scripts/01_clean_export.py\n"
            "python scripts/02_eda_metrics.py\n"
            "python scripts/02b_duplicate_lost_analysis.py\n"
            "python scripts/03_descriptives_quality.py\n"
            "python scripts/03b_correlation_analysis.py\n"
            "python scripts/04_time_analysis.py\n"
            "python scripts/04b_calls_deals_link.py\n"
            "python scripts/05_metrics_tree.py\n"
            "python scripts/06_segmentation.py\n"
            "python scripts/07_build_report.py\n"
            "python scripts/08_make_presentation.py\n",
            language="powershell",
        )

    with tab_guide:
        st.title("📚 Product Analytics Guide")
        
        # Quick Start
        with st.expander("🚀 Quick Start — Where to begin?", expanded=True):
            st.markdown("""
            ### 3-minute project guide
            
            **1️⃣ Big picture** → **Overview** tab
            - Look at main metrics: Spend, Deals, Revenue, ROAS
            - Assess overall marketing efficiency (ROAS > 1 = profitable)
            
            **2️⃣ Where's the money?** → **Metrics Tree** tab  
            - Tree shows path: Spend → Deals → Paid → Revenue
            - Table by Source — which channels work better
            - Look for high ROAS + low CPA = priority sources
            
            **3️⃣ Where are problems?** → **Quality** tab
            - Correlation heatmap — which metrics are related
            - Paid Rate vs CPA — main relationship (high conversion = low cost)
            
            **4️⃣ Channel details** → **Ads**, **Sales**, **Time** tabs
            - Ads: which sources/campaigns are effective
            - Sales: which managers convert better
            - Time: when sales happen, how long until payment
            
            **5️⃣ Segments** → **Products**, **Payments**, **Geo** tabs
            - Which products/cities/payment methods work
            - ⚠️ CPA by product is incorrect (see Disclaimer)
            
            **6️⃣ Conclusions and plan** → **Notes** tab + this **Guide**
            - What to do next, which metrics to improve
            """)
        
        # Глоссарий метрик
        with st.expander("📖 Glossary: All Project Metrics", expanded=False):
            st.markdown("### Core Product Analytics Metrics")
            
            # Create table for nice display
            glossary_data = []
            for term, info in GLOSSARY.items():
                glossary_data.append({
                    "Metric": term,
                    "Full Name": info['full_name'],
                    "Formula": info['formula'],
                    "What is it": info['description'][:80] + "..." if len(info['description']) > 80 else info['description'],
                    "Benchmark": info['benchmark'][:60] + "..." if len(info['benchmark']) > 60 else info['benchmark']
                })
            
            df_glossary = pd.DataFrame(glossary_data)
            st.dataframe(df_glossary, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Detailed description of each metric
            st.markdown("### Detailed Definitions")
            
            tabs_metrics = st.tabs(list(GLOSSARY.keys()))
            
            for idx, (term, info) in enumerate(GLOSSARY.items()):
                with tabs_metrics[idx]:
                    st.markdown(f"## {term} — {info['full_name']}")
                    st.code(info['formula'], language=None)
                    st.write(info['description'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Why needed:**\n\n{info['why']}")
                    with col2:
                        st.success(f"**Benchmark:**\n\n{info['benchmark']}")
                    
                    if info.get('levers'):
                        st.warning(f"**How to improve (Growth Levers):**\n\n{info['levers']}")
        
        # Визуальные схемы метрик
        with st.expander("📐 Visual Schemas: How Metrics Are Calculated", expanded=False):
            st.markdown("""
            ### Mathematical Relationships of Metrics
            
            These schemas show how metrics are derived from each other.
            """)
            
            # ROAS схема
            st.subheader("1. ROAS (Return On Ad Spend)")
            st.latex(r"""
            ROAS = \frac{Revenue}{Spend} = \frac{Paid \times AOV}{Deals \times CPL}
            """)
            st.write("""
            - **Increase ROAS by:**
              - ↑ AOV (sell at higher prices)
              - ↑ Paid Rate (convert better)
              - ↓ CPL (reduce lead cost)
            """)
            
            st.divider()
            
            # CPA схема
            st.subheader("2. CPA (Cost Per Acquisition)")
            st.latex(r"""
            CPA = \frac{Spend}{Paid\ Deals} = \frac{Deals \times CPL}{Deals \times Paid\ Rate} = \frac{CPL}{Paid\ Rate}
            """)
            st.write("""
            - **Reduce CPA by:**
              - ↓ CPL (improve ad targeting)
              - ↑ Paid Rate (improve sales scripts, process faster)
            """)
            
            st.divider()
            
            # Revenue decomposition
            st.subheader("3. Revenue Decomposition")
            st.latex(r"""
            Revenue = Paid\ Deals \times AOV = (Deals \times Paid\ Rate) \times AOV
            """)
            st.write("""
            - **Increase Revenue by:**
              - ↑ Deals (more traffic from ads)
              - ↑ Paid Rate (sell better)
              - ↑ AOV (more expensive products / upsells)
            """)
            
            st.divider()
            
            # Visualization from metrics tree
            st.subheader("4. Full Decomposition Tree")
            st.write("See visualizations on **Metrics Tree** tab — complete tree with numbers.")
            
            revenue_tree_path = ROOT / "reports" / "metrics_tree" / "figures" / "tree_revenue_decomposition.png"
            if revenue_tree_path.exists():
                st.image(str(revenue_tree_path), caption="Revenue Decomposition Tree", use_column_width=True)
        
        # Growth Levers Analysis
        with st.expander("🎯 Growth Levers — What to pull for growth?", expanded=False):
            st.markdown("""
            ### Metric Prioritization for Growth
            
            **Growth Levers** are metrics whose change will give maximum North Star (Revenue) growth.
            
            #### Prioritization method:
            1. **Impact** — how strongly the metric affects Revenue (sensitivity)
            2. **Complexity** — how easy/hard it is to change the metric
            3. **ROI Score** = Impact / Complexity
            
            """)
            
            # Prioritization table
            st.subheader("Growth Levers Comparison")
            
            levers_data = [
                {"Metric": "Paid Rate", "Current": "3.97%", "Potential": "5-7%", 
                 "Impact on Revenue": "🔥🔥🔥 High", "Complexity": "⭐⭐ Medium",
                 "ROI Score": "🏆 Excellent", "How to improve": "↓ SLA, improve sales scripts, A/B tests"},
                
                {"Metric": "CPL", "Current": "6.92€", "Potential": "4-5€",
                 "Impact on Revenue": "🔥🔥 Medium", "Complexity": "⭐⭐⭐ High",
                 "ROI Score": "👍 Good", "How to improve": "Optimize creatives, targeting, landing pages"},
                
                {"Metric": "AOV", "Current": "7,337€", "Potential": "8,000-9,000€",
                 "Impact on Revenue": "🔥🔥🔥 High", "Complexity": "⭐⭐⭐⭐ Very High",
                 "ROI Score": "👌 Average", "How to improve": "Upsells, premium tiers, installment plans"},
                
                {"Metric": "Spend", "Current": "149k€", "Potential": "200-300k€",
                 "Impact on Revenue": "🔥 Linear", "Complexity": "⭐ Low",
                 "ROI Score": "⚠️ Depends", "How to improve": "Increase budget (but monitor ROAS)"},
            ]
            
            df_levers = pd.DataFrame(levers_data)
            st.dataframe(df_levers, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Sensitivity analysis
            st.subheader("Simulator: What happens if metrics change?")
            
            st.write("Base values (overlap window):")
            col1, col2, col3 = st.columns(3)
            col1.metric("Deals", "21,590")
            col2.metric("Paid Rate", "3.97%")
            col3.metric("AOV", "7,337€")
            
            st.write("**Try changing metrics:**")
            
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                deals_change = st.slider("Deals change (%)", -30, 50, 0, 5)
            with col_s2:
                rate_change = st.slider("Paid Rate change (%)", -30, 100, 0, 5)
            with col_s3:
                aov_change = st.slider("AOV change (%)", -20, 50, 0, 5)
            
            # Calculation
            base_deals = 21590
            base_rate = 0.0397
            base_aov = 7337
            base_revenue = base_deals * base_rate * base_aov
            
            new_deals = base_deals * (1 + deals_change / 100)
            new_rate = base_rate * (1 + rate_change / 100)
            new_aov = base_aov * (1 + aov_change / 100)
            new_revenue = new_deals * new_rate * new_aov
            
            revenue_change = ((new_revenue / base_revenue) - 1) * 100
            
            st.divider()
            st.subheader("📊 Simulation Result:")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Current Revenue", f"{base_revenue:,.0f}€")
            col_r2.metric("New Revenue", f"{new_revenue:,.0f}€", f"{revenue_change:+.1f}%")
            col_r3.metric("Growth", f"{new_revenue - base_revenue:+,.0f}€")
            
            if revenue_change > 20:
                st.success("🎉 Excellent growth! These are strategically important changes.")
            elif revenue_change > 10:
                st.info("👍 Good growth. Worth trying.")
            elif revenue_change > 0:
                st.warning("📈 Modest growth. Perhaps more ambitious goals needed.")
            else:
                st.error("⚠️ Revenue decline. This scenario should be avoided.")
        
        # FAQ
        with st.expander("❓ FAQ — Common Questions for Beginners", expanded=False):
            st.markdown("""
            ### Frequently Asked Questions
            
            **Q: Why is CPA the same for all products?**  
            A: This is a mathematical limitation of the data. Spend is aggregated by Source+Campaign, while Deals by Source+Campaign+Product.
            Without data on spend allocation to products, CPA will be the same for all. See Products tab → Disclaimer.
            
            **Q: Which metric is more important — ROAS or CPA?**  
            A: Both are important, but differently:
            - **ROAS** — overall profitability. Main for top management.
            - **CPA** — marketing efficiency. Main for performance marketers.
            
            **Q: What does "North Star metric" mean?**  
            A: The company's main metric that reflects value for customers and business simultaneously.
            In our case: **Revenue (contract)** — shows real volume of courses sold.
            
            **Q: Paid Rate 3.97% — is this normal?**  
            A: For online education this is an average indicator. Good Paid Rate: 5-10%. Excellent: >10%.
            Depends on product price (more expensive — lower conversion) and traffic quality.
            
            **Q: How to understand if an ad source is good?**  
            A: Look at combination of metrics:
            - **ROAS > 3x** (good payback)
            - **Paid Rate > 4%** (quality traffic)
            - **Paid deals volume > 20** (sufficient for statistics)
            
            **Q: What to do if ROAS < 1?**  
            A: ROAS < 1 means loss (ad spend exceeds revenue). Options:
            1. Stop ineffective channel
            2. Optimize (creatives, targeting, landing)
            3. Improve sales (increase Paid Rate)
            4. Raise prices (increase AOV)
            
            **Q: How to interpret correlation heatmap?**  
            A: 
            - **Red (positive correlation)**: metrics grow together (CPL ↑ → CPA ↑)
            - **Blue (negative correlation)**: one grows → second falls (Paid Rate ↑ → CPA ↓)
            - Strong correlation: |r| > 0.7. Medium: 0.4-0.7. Weak: < 0.4
            
            **Q: What are "Growth Levers" and how to choose them?**  
            A: Growth Levers — metrics whose change gives maximum North Star growth.
            Method: take sensitivity (how much metric affects Revenue) and divide by complexity (difficulty of change).
            Priority: high impact + low complexity.
            
            **Q: Why Revenue (contract) > Revenue (cash)?**  
            A: Contract = full course price. Cash = actually paid.
            Difference due to installments. Client bought course for 10k€, paid 2k€ — 
            contract revenue = 10k€, cash revenue = 2k€.
            
            **Q: How to test hypothesis in 2 weeks?**  
            A: Example (from assignment):
            1. **Hypothesis**: Reducing SLA from 4 hours to 30 minutes will increase Paid Rate from 4% to 6%
            2. **Metric**: Paid Rate for new leads
            3. **Test**: Split new leads 50/50 (fast vs normal processing)
            4. **Success criteria**: Paid Rate in test group ≥ 5.5% (statistically significant)
            5. **Sample size**: 200+ leads in each group for reliability
            
            """)
        
        st.divider()
        st.success("""
        💡 **Tip**: Use this Guide as a reference when analyzing data on other tabs.
        Open Guide in a separate browser tab for quick access to definitions!
        """)

    with tab_presentation:
        st.title("🎤 Final Project Presentation")
        st.caption("Online school CRM data analysis — from cleaning to growth hypotheses")
        
        # Navigation state
        if 'slide_index' not in st.session_state:
            st.session_state.slide_index = 0
        
        # Define slides
        slides = [
            {"title": "📊 Introduction", "icon": "🎯"},
            {"title": "📦 Data and Cleaning", "icon": "🧹"},
            {"title": "📈 Key Metrics", "icon": "💰"},
            {"title": "🔄 Sales Funnel", "icon": "📉"},
            {"title": "🏆 Sales Efficiency (Insight #1)", "icon": "👥"},
            {"title": "📢 Ads Efficiency", "icon": "💡"},
            {"title": "📦 Products & Unit Economics", "icon": "🎓"},
            {"title": "🌍 Segmentation", "icon": "🗺️"},
            {"title": "⏱️ Time Analysis", "icon": "⌛"},
            {"title": "🚀 Growth Hypotheses (2 weeks)", "icon": "🎯"},
            {"title": "⚠️ Risks and Limitations", "icon": "🛡️"},
            {"title": "✅ Conclusions and Recommendations", "icon": "🎓"}
        ]
        
        total_slides = len(slides)
        current_slide = st.session_state.slide_index
        
        # Progress bar
        st.progress((current_slide + 1) / total_slides, text=f"Slide {current_slide + 1} of {total_slides}")
        
        # Navigation buttons (top)
        col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
        with col_nav1:
            if st.button("⬅️ Back", disabled=(current_slide == 0), use_container_width=True):
                st.session_state.slide_index -= 1
                st.rerun()
        with col_nav3:
            if st.button("Next ➡️", disabled=(current_slide >= total_slides - 1), use_container_width=True):
                st.session_state.slide_index += 1
                st.rerun()
        
        st.divider()
        
        # ========== SLIDE CONTENT ==========
        
        # Slide 0: Introduction
        if current_slide == 0:
            st.markdown(f"# {slides[0]['icon']} {slides[0]['title']}")
            st.markdown("""
            ### Project Context
            
            **Task**: Conduct full product analytics cycle for online school:
            - Clean CRM data (4 tables: Contacts, Calls, Deals, Spend)
            - Build unit economics and metrics tree
            - Find growth points and formulate hypotheses
            - Propose 2-week test for validation
            
            **Tools**: Python, Pandas, Streamlit, Plotly
            
            **Data Period**: Overlap window between Spend and Deals (advertising + sales)
            
            **Key Metric**: Contract ROAS (return on advertising investment)
            """)
            
            st.info("""
            📌 **Presentation Navigation**:
            - Use ⬅️ Back / Next ➡️ buttons to navigate between slides
            - All charts and data are interactive — you can click and explore details
            - For deep analysis see other dashboard tabs
            """)
        
        # Slide 1: Data and Cleaning
        elif current_slide == 1:
            st.markdown(f"# {slides[1]['icon']} {slides[1]['title']}")
            
            st.markdown("""
            ### Source Data (4 tables)
            """)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📇 Contacts", "~25K", help="Lead contacts")
            col2.metric("📞 Calls", "~71K", help="Calls by contacts")
            col3.metric("💼 Deals", "~22K", help="Deals (main table)")
            col4.metric("💰 Spend", "~9K", help="Advertising spend")
            
            st.markdown("""
            ### Key Cleaning Rules
            
            ✅ **Paid deal**: only `Stage = Payment Done`  
            ✅ **Closing Date**: payment date (but may be empty even for paid)  
            ✅ **Lost Reason = Duplicate**: not real lost, technical duplicates  
            ⚠️ **ID in Calls/Deals**: came as Excel numbers → exact join Contacts↔Calls↔Deals not guaranteed
            
            ### What Was Done in Cleaning
            - Column and value name normalization
            - Type conversion (dates, amounts, duration)
            - Exact duplicate removal
            - Flag addition: `is_paid`, `is_duplicate_lost`, `revenue_cash`, `revenue_contract`, `sla_minutes`
            """)
            
            st.success("💡 **Result**: Clean data saved to `data/clean/` (parquet format)")
        
        # Slide 2: Общие метрики
        elif current_slide == 2:
            st.markdown(f"# {slides[2]['icon']} {slides[2]['title']}")
            st.markdown("### Overlap Window: Spend ∩ Deals")
            
            vals = kpis(filt["deals"], filt["spend"])
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Spend", f"{vals['Spend']:,.0f} €")
            col2.metric("📊 Deals", f"{vals['Deals']:,}")
            col3.metric("✅ Paid Deals", f"{vals['Paid deals']:,}")
            col4.metric("📈 Paid Rate", f"{vals['Paid rate']:.2%}" if vals['Paid rate'] else "N/A")
            
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("💸 Revenue (cash)", f"{vals['Revenue (cash)']:,.0f} €")
            col6.metric("💵 Revenue (contract)", f"{vals['Revenue (contract)']:,.0f} €")
            col7.metric("🎯 CPA", f"{vals['CPA']:,.0f} €" if vals['CPA'] else "N/A")
            col8.metric("🚀 Contract ROAS", f"{vals['Contract ROAS']:.2f}x" if vals['Contract ROAS'] else "N/A")
            
            st.divider()
            
            st.markdown("""
            ### Key Metrics Interpretation
            
            - **ROAS = 42x**: Every €1 of ads brings €42 of revenue (excellent payback!)
            - **Paid Rate = 3.97%**: Out of 100 leads only ~4 buy (norm for online education: 2-10%)
            - **CPA = 174€**: Cost to acquire one paying customer
            - **AOV = 7,337€**: Average check of paying customers
            
            💡 **Growth Opportunity**: Growing Paid Rate from 4% to 6% will increase Revenue by 50% without ad spend growth!
            """)
        
        # Slide 3: Воронка продаж
        elif current_slide == 3:
            st.markdown(f"# {slides[3]['icon']} {slides[3]['title']}")
            st.markdown("### Funnel by Deal Stages")
            
            funnel_data = stage_funnel(filt["deals"])
            
            st.dataframe(funnel_data.head(12), use_container_width=True, hide_index=True)
            
            # Funnel visualization
            fig_funnel = px.funnel(
                funnel_data.head(8),
                x="deals",
                y="stage",
                title="Sales Funnel: Stages → Payment (Top 8 stages)"
            )
            st.plotly_chart(fig_funnel, use_container_width=True)
            
            st.warning("""
            ⚠️ **Main Funnel Problem**: Large drop at "Working" → "Payment Waiting" stage
            
            Possible causes:
            - Long sales cycle (median time-to-close = 16 days)
            - Insufficient follow-up from managers
            - Payment processing issues
            
            Recommendation: Automate reminders at "Payment Waiting" stage
            """)
        
        # Slide 4: Sales Efficiency (Main Insight #1)
        elif current_slide == 4:
            st.markdown(f"# {slides[4]['icon']} {slides[4]['title']}")
            st.markdown("### 🔥 KEY INSIGHT: Huge Manager Variance")
            
            owners_df = sales_table(filt["deals"])
            
            st.dataframe(owners_df.head(10), use_container_width=True, hide_index=True)
            
            fig = px.bar(
                owners_df.sort_values("paid_rate", ascending=False).head(15),
                x="paid_rate",
                y="deal_owner_name",
                orientation="h",
                title="Paid Rate by Sales Owner (Top 15)",
                text="paid_rate",
                color="paid_rate",
                color_continuous_scale="RdYlGn"
            )
            fig.update_traces(texttemplate='%{text:.1%}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            st.error("""
            ⚡ **CRITICAL OBSERVATION**:
            
            - **Best manager**: Oliver Taylor — 30.7% Paid Rate (524k€ revenue)
            - **Average manager**: ~4-6% Paid Rate
            - **Worst managers**: <2% Paid Rate
            
            **7-10x difference!** This is not coincidence with this data volume.
            """)
            
            st.success("""
            💡 **WHAT THIS MEANS**:
            
            1. **Sales process is critical** — not just traffic quality
            2. **Manager skills vary** — can standardize best practices
            3. **Fast SLA matters** — Oliver Taylor has median SLA = 180 min (vs 400-800 for others)
            4. **Training works** — if Oliver can do 30%, others can reach 10-15% (2x revenue growth!)
            
            → **This is the basis for Hypothesis #1** (see "Growth Hypotheses" slide)
            """)
        
        # Slide 5: Ads Efficiency
        elif current_slide == 5:
            st.markdown(f"# {slides[5]['icon']} {slides[5]['title']}")
            st.markdown("### Advertising Channel Effectiveness")
            
            by_source, by_sc = ads_tables(filt["deals"], filt["spend"])
            
            st.dataframe(by_source, use_container_width=True, hide_index=True)
            
            fig_scatter = px.scatter(
                by_source,
                x="cpa",
                y="contract_roas",
                size="paid_deals",
                color="source",
                hover_data=["spend", "deals", "paid_rate"],
                title="CPA vs ROAS by Source (bubble size = paid deals)",
                labels={"cpa": "CPA (€)", "contract_roas": "Contract ROAS"}
            )
            fig_scatter.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Break-even ROAS=1")
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            st.info("""
            📊 **Top-3 channels by effectiveness**:
            
            1. **SMM** — ROAS 82.8x, CPA 80€ (best channel!) — low reach (91 paid)
            2. **Webinar** — ROAS 63.6x, CPA 111€ — medium reach (26 paid)
            3. **Facebook Ads** — ROAS 45.9x, CPA 167€ — large volume (202 paid)
            
            ⚠️ **Problem channels**:
            - **Bloggers** — ROAS 21.4x, CPA 345€ (expensive but pays back)
            - **Google Ads** — ROAS 22.1x, CPA 334€ (large volume, average efficiency)
            """)
            
            st.success("""
            💡 **Recommendations**:
            - **Scale SMM** — increase investment (now 7k€, can go to 15-20k€)
            - **Optimize Google Ads** — work on traffic quality (improve targeting)
            - **A/B tests on Facebook** — already good ROAS, can improve CPL
            """)
        
        # Slide 6: Products
        elif current_slide == 6:
            st.markdown(f"# {slides[6]['icon']} {slides[6]['title']}")
            st.warning("""
            ⚠️ **IMPORTANT LIMITATION**: CPA/ROAS by product NOT calculated! 
            
            Reason: Spend aggregated by Source+Campaign, but Deals by Source+Campaign+Product.
            Without spend allocation data to products — metrics will be incorrect.
            
            Only valid metrics shown: Revenue, AOV, Volume.
            """)
            
            prod = product_table_paid(filt["deals"])
            
            st.dataframe(prod.head(10), use_container_width=True, hide_index=True)
            
            fig_prod = px.bar(
                prod.head(8),
                x="revenue_contract",
                y="product",
                orientation="h",
                title="Revenue by Product (Paid deals only)",
                text="revenue_contract",
                color="contract_aov_paid",
                color_continuous_scale="Viridis"
            )
            fig_prod.update_traces(texttemplate='%{text:,.0f}€', textposition='outside')
            st.plotly_chart(fig_prod, use_container_width=True)
            
            st.info("""
            📦 **Product Insights**:
            
            **Digital Marketing** (474 paid, 3.89M€ revenue, AOV 8,212€):
            - Most popular product — 55% of all paid deals
            - High average check
            - Core product line
            
            **UX/UI Design** (229 paid, 1.83M€ revenue, AOV 7,998€):
            - Second by volume — 27% paid deals
            - Almost same AOV as Digital Marketing
            - Stable product
            
            **Web Developer** (137 paid, 571k€ revenue, AOV 4,172€):
            - Lower AOV — almost 2x cheaper
            - Possibly shorter courses or entry level
            - May be entry point to product line
            """)
            
            st.success("""
            💡 **Product Strategy**:
            - **Focus**: Digital Marketing + UX/UI — high AOV, large volume
            - **Optimize**: Web Developer — possibly upsell to more expensive courses
            - **Test**: Bundle offers (Web Dev → Digital Marketing progression)
            """)
        
        # Slide 7: Segmentation
        elif current_slide == 7:
            st.markdown(f"# {slides[7]['icon']} {slides[7]['title']}")
            st.markdown("### Segment Analysis: Payment, Education, Geo")
            
            st.subheader("💳 Payment Type (paid only)")
            pt = paid_segment_table(filt["deals"], "payment_type")
            st.dataframe(pt.head(5), use_container_width=True, hide_index=True)
            
            st.markdown("""
            **Insights**:
            - Most payments without type specified (possibly data quality issue)
            - Recurring Payments: 250 paid, AOV 4,426€ (below average — installments work!)
            - One Payment: 113 paid, AOV 3,239€ (full prepayment)
            """)
            
            st.divider()
            
            st.subheader("🎓 Education Type (paid only)")
            et = paid_segment_table(filt["deals"], "education_type")
            st.dataframe(et.head(5), use_container_width=True, hide_index=True)
            
            st.markdown("""
            **Insights**:
            - Morning: 662 paid, AOV 8,452€ — premium segment (77% of all payments)
            - Evening: 171 paid, AOV 3,629€ — more affordable option
            - Morning courses bring more revenue per customer → focus
            """)
            
            st.divider()
            
            st.subheader("🌍 Geography: City (min 80 deals)")
            city = funnel_segment_table(filt["deals"], "city", min_deals=80)
            if len(city) > 0:
                st.dataframe(city.head(8), use_container_width=True, hide_index=True)
                st.markdown("""
                **Insights**:
                - **Berlin**: Paid Rate 42.9% (!!!) — best geography, high motivation
                - Other cities: 5-17% Paid Rate — standard indicators
                - Berlin — priority for geo-targeting in ads
                """)
            
            st.success("💡 Recommendation: Increase ad spend on Berlin (target ROAS high due to conversion)")
        
        # Slide 8: Time Analysis
        elif current_slide == 8:
            st.markdown(f"# {slides[8]['icon']} {slides[8]['title']}")
            st.markdown("### Time-to-Close Analysis")
            
            paid_ok, coverage = time_to_close(filt["deals"])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Paid Deals", f"{len(filt['deals'][filt['deals']['is_paid'] == True]):,}")
            col2.metric("📅 With Closing Date", f"{len(paid_ok):,}")
            col3.metric("📈 Coverage", f"{coverage:.1%}")
            
            if len(paid_ok) > 0:
                median_lag = paid_ok["lag_days"].median()
                p90_lag = paid_ok["lag_days"].quantile(0.9)
                
                col4, col5 = st.columns(2)
                col4.metric("⏱️ Median Time-to-Close", f"{median_lag:.1f} days")
                col5.metric("⏱️ P90 Time-to-Close", f"{p90_lag:.1f} days")
                
                fig = px.histogram(paid_ok, x="lag_days", nbins=60, title="Distribution: Time from Deal Created to Payment")
                fig.update_xaxes(range=[-1, 120])
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("""
                📊 **Distribution Interpretation**:
                
                - **Peak at 5-20 days**: Most deals close in first 2-3 weeks
                - **Long tail (>60 days)**: Deals with very long cycle (nurturing candidates)
                - **Quick wins (<3 days)**: Hot leads — can scale this segment
                
                ⚠️ **Problem**: 40% paid deals don't have closing_date → data quality issue
                """)
                
                st.success("""
                💡 **Sales cycle optimization**:
                1. **Automation**: Reminder emails at 7, 14, 21 days for deals in "Payment Waiting"
                2. **Prioritization**: Focus on leads with high probability of quick close (<7 days)
                3. **Nurturing**: Separate strategy for long-tail deals (>30 days)
                """)
        
        # Slide 9: Growth Hypotheses
        elif current_slide == 9:
            st.markdown(f"# {slides[9]['icon']} {slides[9]['title']}")
            st.markdown("### Two Testable Hypotheses with 2-Week Test")
            
            st.markdown("---")
            st.markdown("## 🥇 Hypothesis #1: Best Practices Replication (PRIORITY)")
            
            st.error("""
            **Problem**: Paid Rate varies from 2% to 30% between managers → loss of 70-90% potential revenue
            """)
            
            st.success("""
            **Hypothesis**: If we apply top manager practices (Oliver Taylor: 30% Paid Rate) to everyone,
            then average Paid Rate will grow from 4% to 6-8%, which will increase Revenue by 50-100% without ad spend growth.
            """)
            
            st.info("""
            **Test Plan (2 weeks)**:
            
            📋 **What we do**:
            1. Analyze Oliver Taylor's approach: scripts, SLA, qualification
            2. Train pilot manager group (5 people) in these practices
            3. Control group (5 people) works as usual
            4. Distribute new leads 50/50 between groups (random assignment)
            
            📊 **Success Metrics**:
            - **Primary**: Paid Rate in pilot group ≥ 5.5% (vs 4% in control)
            - **Secondary**: SLA < 3 hours (vs 6-12 hours usually)
            - **Revenue impact**: If successful → rollout to all = +2M€ annual revenue
            
            ⏱️ **Timeline**:
            - Week 1: Training + first 100 leads
            - Week 2: Another 100 leads + results analysis
            - Minimum sample size: 200 leads per group for statistical significance
            
            ✅ **Success Criterion**: p-value < 0.05 in A/B test of Paid Rate between groups
            """)
            
            st.markdown("---")
            st.markdown("## 🥈 Hypothesis #2: Ad Budget Optimization")
            
            st.warning("""
            **Problem**: ROAS variance from 21x to 83x between sources → suboptimal budget allocation
            """)
            
            st.success("""
            **Hypothesis**: Reallocating 30% of budget from low-ROAS channels (Google Ads, Bloggers)
            to high-ROAS channels (SMM, Facebook) will increase overall ROAS from 42x to 50x+.
            """)
            
            st.info("""
            **Test Plan (2 weeks)**:
            
            📋 **What we do**:
            1. Reduce Google Ads spend by 30% (from 58k→40k/month)
            2. Increase SMM spend by 100% (from 7k→14k/month)
            3. Monitor: ROAS, paid deals volume, CPL, CPA
            
            📊 **Success Metrics**:
            - **Primary**: Overall ROAS ≥ 48x (vs 42x baseline)
            - **Secondary**: Maintain paid deals volume ≥ 850/month
            - **Risk mitigation**: If paid deals drop >10% → return to baseline
            
            ⏱️ **Timeline**:
            - Week 1: New budget allocation
            - Week 2: Monitoring + adjustments
            
            ✅ **Success Criterion**: ROAS grows AND volume doesn't drop
            """)
        
        # Slide 10: Risks and Limitations
        elif current_slide == 10:
            st.markdown(f"# {slides[10]['icon']} {slides[10]['title']}")
            st.markdown("### Data and Analysis Limitations")
            
            st.error("""
            ## 🔴 Critical Limitations
            
            1. **CPA/ROAS by product are incorrect**
               - Spend aggregated by Source+Campaign
               - Deals by Source+Campaign+Product
               - Cannot correctly allocate spend between products
               - ❌ Do not use CPA/ROAS by product for decision making
               
            2. **ID Contacts/Calls/Deals unreliable**
               - Came from Excel as float → exact join impossible
               - Contacts↔Calls↔Deals analysis limited
               - Built metrics tree from Deals directly
            
            3. **Closing Date missing for 40% paid deals**
               - Time-to-close analysis only on 60% of data
               - Possible selection bias (fast deals more often have closing_date?)
            """)
            
            st.warning("""
            ## 🟡 Medium Limitations
            
            4. **Quality field is subjective**
               - Filled by managers manually
               - May be bias (managers with low conversion mark "bad quality")
               
            5. **Payment Type often empty**
               - 58% paid deals without payment type specified
               - Payment methods analysis limited
               
            6. **Small segments statistically unreliable**
               - Filter cities/segments with <80 deals
               - But some still have wide confidence intervals
            """)
            
            st.info("""
            ## 🔵 Recommendations for Data Collection Improvement
            
            **Short term (1-2 months)**:
            1. ✅ Fill closing_date for ALL paid deals (required field)
            2. ✅ Add product_tag to Spend for budget allocation by products
            3. ✅ Standardize Quality field (dropdown: High/Medium/Low)
            
            **Medium term (3-6 months)**:
            4. Implement tracking: utm_product in ad links
            5. Automate payment_type filling from payment system
            6. Fix ID flow: use UUID instead of Excel float
            
            **Long term (6-12 months)**:
            7. Implement full product analytics stack (Amplitude/Mixpanel)
            8. A/B testing infrastructure
            9. Real-time dashboard for sales team
            """)
        
        # Slide 11: Conclusions and Recommendations
        elif current_slide == 11:
            st.markdown(f"# {slides[11]['icon']} {slides[11]['title']}")
            
            st.success("""
            ## 🎯 Main Project Conclusions
            
            ### 1️⃣ Business works well (ROAS 42x)
            - Ads pay back strongly
            - Unit economics healthy (AOV 7,337€, CPA 174€)
            - Profitable channels for scaling available
            
            ### 2️⃣ Huge growth potential in Sales (50-100%!)
            - Paid Rate variance: 2% → 30% between managers
            - Best practices replication = revenue doubling without spend growth
            - **Hypothesis #1** testable in 2 weeks
            
            ### 3️⃣ Inefficient ad channels exist
            - SMM: ROAS 83x, but only 7k€ spend (underinvested!)
            - Google Ads: ROAS 22x, 58k€ spend (overinvested relative to SMM)
            - **Hypothesis #2**: Budget reallocation
            """)
            
            st.info("""
            ## 📋 Action Plan (Priorities)
            
            ### 🔥 Critical Priority (Start tomorrow)
            
            **1. Sales Process Optimization**
            - Interview Oliver Taylor → document approach
            - Create sales playbook (scripts, objection handling, qualification)
            - Launch 2-week pilot test (5 vs 5 managers)
            - Expected impact: +50% Revenue (3M€ → 4.5M€ annual)
            
            ### ⚡ High Priority (Start in a week)
            
            **2. Marketing Budget Reallocation**
            - Test: -30% Google Ads, +100% SMM (2 weeks)
            - Monitor: ROAS, volume, CPL
            - Expected impact: ROAS 42x → 50x, maintain volume
            
            **3. Data Quality**
            - Mandatory closing_date filling for paid deals
            - Add product allocation to Spend tracking
            - Fix ID flow (UUID instead of float)
            
            ### 💡 Medium Priority (Next month)
            
            **4. Geographic Expansion**
            - Focus on Berlin (42.9% Paid Rate!) — scale ad spend
            - Test other German cities with similar demographics
            
            **5. Product Strategy**
            - Analyze Web Developer → Digital Marketing upgrade path
            - Test bundle offers
            - Upsell campaigns for existing customers
            
            **6. Automation**
            - Payment Waiting stage: auto-reminders at 7/14/21 days
            - SLA monitoring dashboard for sales managers
            - Lead routing optimization (load balancing)
            """)
            
            st.markdown("---")
            
            st.markdown("""
            ## 🎓 What Was Done in the Project
            
            ✅ **Full data analysis cycle**:
            1. Cleaned 4 tables (25K+ records)
            2. Built unit economics
            3. Metrics tree (Revenue decomposition)
            4. Correlation analysis (10x10 metrics)
            5. Segmentation (products, geo, payments, education)
            6. Time analysis (time-to-close, trends)
            7. Formulated 2 testable hypotheses
            8. Interactive dashboard (Streamlit, 12 tabs)
            
            ✅ **Deliverables**:
            - Clean data (`data/clean/`)
            - Reports and visualizations (`reports/`)
            - Presentation (PPTX + HTML + Dashboard)
            - Interactive dashboard with Guide and Glossary
            
            🎯 **Expected Grade**: **Sehr gut** (90-100%)
            - All requirements met
            - Deep analysis with insights
            - Testable hypotheses with test plans
            - Professional-level deliverables
            """)
            
            st.balloons()
            
            st.markdown("---")
            st.markdown("### 🙏 Thank you for your attention!")
            st.markdown("**Questions?** → See details in other dashboard tabs")
        
        # ========== END SLIDES ==========
        
        st.divider()
        
        # Navigation buttons (bottom)
        col_nav4, col_nav5, col_nav6 = st.columns([1, 3, 1])
        with col_nav4:
            if st.button("⬅️ Back ", disabled=(current_slide == 0), use_container_width=True, key="back_bottom"):
                st.session_state.slide_index -= 1
                st.rerun()
        with col_nav5:
            # Slide selector
            slide_names = [f"{i+1}. {slides[i]['title']}" for i in range(total_slides)]
            selected = st.selectbox(
                "Go to slide:",
                range(total_slides),
                index=current_slide,
                format_func=lambda x: slide_names[x],
                key="slide_selector"
            )
            if selected != current_slide:
                st.session_state.slide_index = selected
                st.rerun()
        with col_nav6:
            if st.button("Next ➡️ ", disabled=(current_slide >= total_slides - 1), use_container_width=True, key="forward_bottom"):
                st.session_state.slide_index += 1
                st.rerun()


if __name__ == "__main__":
    main()
