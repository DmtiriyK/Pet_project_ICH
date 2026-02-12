from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "segments"


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)


def _save_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def paid_segments(deals: pd.DataFrame, col: str) -> pd.DataFrame:
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
    out["cash_aov_paid"] = out["revenue_cash"] / out["paid_deals"].replace(0, np.nan)
    out["contract_aov_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    out["share_paid_deals_pct"] = (out["paid_deals"] / out["paid_deals"].sum() * 100).round(2)
    return out.sort_values("revenue_contract", ascending=False)


def funnel_segments(deals: pd.DataFrame, col: str, *, min_deals: int = 50) -> pd.DataFrame:
    d = deals.copy()
    d[col] = d[col].fillna("NA")
    out = (
        d.groupby(col, dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    out["paid_rate"] = out["paid_deals"] / out["deals"].replace(0, np.nan)
    out["contract_per_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    out = out[out["deals"] >= min_deals].copy()
    return out.sort_values("revenue_contract", ascending=False)


def plot_segment_viz(df: pd.DataFrame, col_name: str, segment_type: str) -> None:
    """Create visualizations for segment analysis"""
    
    if df.empty:
        print(f"[SKIP] {segment_type}: no data")
        return
    
    top15 = df.head(15).copy()
    
    # 1. Revenue bar chart
    fig1 = px.bar(
        top15,
        y=col_name,
        x="revenue_contract",
        orientation="h",
        title=f"Contract Revenue by {segment_type} (Top 15)",
        labels={"revenue_contract": "Revenue (€)", col_name: segment_type},
        template="plotly_white",
        color="revenue_contract",
        color_continuous_scale="Viridis"
    )
    
    fig1.update_layout(height=max(400, len(top15) * 30), showlegend=False)
    fig1.write_html(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_revenue.html"))
    fig1.write_image(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_revenue.png"), 
                     width=1000, height=max(500, len(top15) * 35))
    
    # 2. Paid deals bar chart
    fig2 = px.bar(
        top15,
        y=col_name,
        x="paid_deals",
        orientation="h",
        title=f"Paid Deals by {segment_type} (Top 15)",
        labels={"paid_deals": "Paid Deals Count", col_name: segment_type},
        template="plotly_white",
        color="contract_aov_paid",
        color_continuous_scale="RdYlGn",
        hover_data=["revenue_contract", "share_paid_deals_pct"]
    )
    
    fig2.update_layout(height=max(400, len(top15) * 30))
    fig2.write_html(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_paid_deals.html"))
    fig2.write_image(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_paid_deals.png"), 
                     width=1000, height=max(500, len(top15) * 35))
    
    # 3. AOV comparison
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        y=top15[col_name],
        x=top15["contract_aov_paid"],
        name="Contract AOV",
        orientation="h",
        marker=dict(color="#1f77b4")
    ))
    
    fig3.update_layout(
        title=f"Average Order Value (AOV) by {segment_type}",
        xaxis_title="AOV (€)",
        yaxis_title=segment_type,
        template="plotly_white",
        height=max(400, len(top15) * 30),
        showlegend=True
    )
    
    fig3.write_html(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_aov.html"))
    fig3.write_image(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_aov.png"), 
                     width=1000, height=max(500, len(top15) * 35))


def plot_funnel_viz(df: pd.DataFrame, col_name: str, segment_type: str) -> None:
    """Create visualizations for funnel segment analysis"""
    
    if df.empty:
        print(f"[SKIP] {segment_type} funnel: no data")
        return
    
    top_by_revenue = df.head(15).copy()
    top_by_rate = df.sort_values("paid_rate", ascending=False).head(15).copy()
    
    # 1. Paid rate comparison
    fig1 = px.bar(
        top_by_rate,
        y=col_name,
        x="paid_rate",
        orientation="h",
        title=f"Paid Rate by {segment_type} (Top 15 by rate)",
        labels={"paid_rate": "Paid Rate", col_name: segment_type},
        template="plotly_white",
        color="paid_rate",
        color_continuous_scale="RdYlGn",
        hover_data=["deals", "paid_deals", "revenue_contract"]
    )
    
    fig1.update_xaxes(tickformat=".1%")
    fig1.update_layout(height=max(400, len(top_by_rate) * 30), showlegend=False)
    fig1.write_html(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_paid_rate.html"))
    fig1.write_image(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_paid_rate.png"), 
                     width=1000, height=max(500, len(top_by_rate) * 35))
    
    # 2. Deals vs Paid scatter
    fig2 = px.scatter(
        df,
        x="deals",
        y="paid_rate",
        size="revenue_contract",
        color="paid_rate",
        hover_name=col_name,
        hover_data=["paid_deals", "contract_per_paid"],
        title=f"Deals vs Paid Rate by {segment_type} (bubble = revenue)",
        labels={"deals": "Total Deals", "paid_rate": "Paid Rate"},
        template="plotly_white",
        color_continuous_scale="RdYlGn"
    )
    
    fig2.update_yaxes(tickformat=".1%")
    fig2.update_layout(height=500)
    fig2.write_html(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_scatter.html"))
    fig2.write_image(str(OUT_DIR / "figures" / f"{segment_type.lower().replace(' ', '_')}_scatter.png"), 
                     width=1000, height=600)


def main() -> None:
    _ensure_dirs()
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")

    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")

    print("[INFO] Generating paid segments...")
    
    # Этап 6: платежи и продукты
    payment_seg = paid_segments(deals, "payment_type")
    _save_csv(payment_seg, "paid_by_payment_type")
    plot_segment_viz(payment_seg, "payment_type", "Payment Type")
    
    product_seg = paid_segments(deals, "product")
    _save_csv(product_seg, "paid_by_product")
    plot_segment_viz(product_seg, "product", "Product")
    
    education_seg = paid_segments(deals, "education_type")
    _save_csv(education_seg, "paid_by_education_type")
    plot_segment_viz(education_seg, "education_type", "Education Type")

    print("[INFO] Generating funnel segments...")
    
    # Этап 7: география / уровень языка (конверсия, выручка)
    city_funnel = funnel_segments(deals, "city", min_deals=80)
    _save_csv(city_funnel, "funnel_by_city_min80")
    plot_funnel_viz(city_funnel, "city", "City")
    
    level_funnel = funnel_segments(deals, "level_of_deutsch", min_deals=80)
    _save_csv(level_funnel, "funnel_by_level_of_deutsch_min80")
    plot_funnel_viz(level_funnel, "level_of_deutsch", "Level of Deutsch")

    notes = {
        "paid_definition": "deals.is_paid == True (Stage = Payment Done)",
        "geo_note": "City/Level of Deutsch сильно разрежены (много NA), поэтому считаем сегменты только при min_deals пороге.",
        "cash_vs_contract": "Везде считаем два вида выручки: cash (Initial Amount Paid) и contract (Offer Total Amount).",
        "visualizations": "Для каждого сегмента созданы 3 графика: revenue, paid deals, AOV (для paid-only) или paid rate (для funnel)."
    }
    _save_json(notes, "notes")

    print("[OK] reports/segments ready (tables + figures)")


if __name__ == "__main__":
    main()

