from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "time"


@dataclass(frozen=True)
class ClosingLagStats:
    paid_deals: int
    paid_with_closing_date: int
    coverage_pct: float
    lag_days_median: float | None
    lag_days_p90: float | None
    lag_days_p99: float | None


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)


def _save_table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_clean() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")
    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    return deals, spend, calls


def build_daily_timeseries(deals: pd.DataFrame, spend: pd.DataFrame, calls: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["date"] = pd.to_datetime(d["created_time"], errors="coerce").dt.date
    deals_daily = (
        d.groupby("date", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )

    s = spend.copy()
    spend_daily = s.groupby("date", dropna=False).agg(spend=("spend", "sum")).reset_index()

    c = calls.copy()
    c["date"] = pd.to_datetime(c["call_start_time"], errors="coerce").dt.date
    calls_daily = c.groupby("date", dropna=False).agg(calls=("call_id", "size")).reset_index()

    ts = deals_daily.merge(spend_daily, on="date", how="outer").merge(calls_daily, on="date", how="outer")
    for col in ["deals", "paid_deals", "revenue_cash", "revenue_contract", "spend", "calls"]:
        ts[col] = pd.to_numeric(ts[col], errors="coerce").fillna(0)

    ts = ts[ts["date"].notna()].copy()
    ts = ts.sort_values("date")

    ts["date"] = pd.to_datetime(ts["date"])
    ts["paid_rate"] = ts["paid_deals"] / ts["deals"].replace(0, np.nan)
    ts["cpa_contract"] = ts["spend"] / ts["paid_deals"].replace(0, np.nan)
    ts["roas_contract"] = ts["revenue_contract"] / ts["spend"].replace(0, np.nan)
    
    # Add 7-day moving averages for smoother trend visualization
    ts["deals_ma7"] = ts["deals"].rolling(window=7, min_periods=1).mean()
    ts["paid_deals_ma7"] = ts["paid_deals"].rolling(window=7, min_periods=1).mean()
    ts["spend_ma7"] = ts["spend"].rolling(window=7, min_periods=1).mean()
    
    return ts


def compute_time_to_close(deals: pd.DataFrame) -> tuple[pd.DataFrame, ClosingLagStats]:
    paid = deals[deals["is_paid"].fillna(False)].copy()
    paid_deals = int(len(paid))

    paid["created_time_dt"] = pd.to_datetime(paid["created_time"], errors="coerce")
    paid["closing_date_dt"] = pd.to_datetime(paid["closing_date"], errors="coerce")
    ok = paid["created_time_dt"].notna() & paid["closing_date_dt"].notna()
    paid_ok = paid[ok].copy()

    paid_ok["lag_days"] = (paid_ok["closing_date_dt"] - paid_ok["created_time_dt"]).dt.total_seconds() / 86400
    paid_ok = paid_ok[paid_ok["lag_days"].notna()].copy()

    coverage_pct = float(round(len(paid_ok) / paid_deals * 100, 2)) if paid_deals else 0.0

    if len(paid_ok):
        stats = ClosingLagStats(
            paid_deals=paid_deals,
            paid_with_closing_date=int(len(paid_ok)),
            coverage_pct=coverage_pct,
            lag_days_median=float(paid_ok["lag_days"].median()),
            lag_days_p90=float(paid_ok["lag_days"].quantile(0.90)),
            lag_days_p99=float(paid_ok["lag_days"].quantile(0.99)),
        )
    else:
        stats = ClosingLagStats(
            paid_deals=paid_deals,
            paid_with_closing_date=0,
            coverage_pct=coverage_pct,
            lag_days_median=None,
            lag_days_p90=None,
            lag_days_p99=None,
        )

    cols = [
        "deal_row_id",
        "deal_owner_name",
        "source",
        "campaign",
        "product",
        "payment_type",
        "created_time_dt",
        "closing_date_dt",
        "lag_days",
        "revenue_cash",
        "revenue_contract",
    ]
    out = paid_ok[[c for c in cols if c in paid_ok.columns]].sort_values("lag_days", ascending=False)
    return out, stats


def plot_timeseries_plotly(ts: pd.DataFrame) -> None:
    """Create interactive timeseries plots with plotly"""
    
    # 1. Deals vs Paid Deals with moving averages
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    
    fig.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["deals"],
            name="Deals (daily)",
            mode="lines",
            line=dict(color="#4c78a8", width=1),
            opacity=0.4
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["deals_ma7"],
            name="Deals (7-day MA)",
            mode="lines",
            line=dict(color="#4c78a8", width=2.5)
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["paid_deals"],
            name="Paid Deals (daily)",
            mode="lines",
            line=dict(color="#f58518", width=1),
            opacity=0.4
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["paid_deals_ma7"],
            name="Paid Deals (7-day MA)",
            mode="lines",
            line=dict(color="#f58518", width=2.5)
        )
    )
    
    fig.update_layout(
        title="Deals & Paid Deals Over Time (with 7-day moving average)",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    fig.write_html(str(OUT_DIR / "figures" / "ts_deals_paid.html"))
    fig.write_image(str(OUT_DIR / "figures" / "ts_deals_paid.png"), width=1200, height=600)
    
    # 2. Spend vs Paid Deals (dual axis)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig2.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["spend"],
            name="Spend (daily)",
            mode="lines",
            line=dict(color="#1f77b4", width=1),
            opacity=0.4
        ),
        secondary_y=False
    )
    
    fig2.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["spend_ma7"],
            name="Spend (7-day MA)",
            mode="lines",
            line=dict(color="#1f77b4", width=2.5)
        ),
        secondary_y=False
    )
    
    fig2.add_trace(
        go.Scatter(
            x=ts["date"],
            y=ts["paid_deals"],
            name="Paid Deals",
            mode="lines",
            line=dict(color="#ff7f0e", width=2),
            fill="tozeroy",
            fillcolor="rgba(255,127,14,0.1)"
        ),
        secondary_y=True
    )
    
    fig2.update_xaxes(title_text="Date")
    fig2.update_yaxes(title_text="Spend (€)", secondary_y=False)
    fig2.update_yaxes(title_text="Paid Deals", secondary_y=True)
    
    fig2.update_layout(
        title="Spend vs Paid Deals Over Time",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    fig2.write_html(str(OUT_DIR / "figures" / "ts_spend_vs_paid.html"))
    fig2.write_image(str(OUT_DIR / "figures" / "ts_spend_vs_paid.png"), width=1200, height=600)
    
    # 3. Paid Rate over Time
    fig3 = go.Figure()
    
    fig3.add_trace(
        go.Scatter(
            x=ts["date"],
            y=(ts["paid_rate"] * 100),
            name="Paid Rate",
            mode="lines",
            line=dict(color="#2ca02c", width=2),
            fill="tozeroy",
            fillcolor="rgba(44,160,44,0.1)"
        )
    )
    
    # Add reference line for mean
    mean_rate = (ts["paid_rate"] * 100).mean()
    fig3.add_hline(
        y=mean_rate,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Mean: {mean_rate:.1f}%",
        annotation_position="right"
    )
    
    fig3.update_layout(
        title=" Paid Rate Over Time (Daily)",
        xaxis_title="Date",
        yaxis_title="Paid Rate (%)",
        hovermode="x",
        template="plotly_white",
        height=450
    )
    
    fig3.write_html(str(OUT_DIR / "figures" / "ts_paid_rate.html"))
    fig3.write_image(str(OUT_DIR / "figures" / "ts_paid_rate.png"), width=1200, height=550)
    
    # 4. ROAS over Time
    fig4 = go.Figure()
    
    # Filter out extreme outliers for better visualization
    ts_viz = ts[ts["roas_contract"].between(0, 20, inclusive="both")].copy()
    
    fig4.add_trace(
        go.Scatter(
            x=ts_viz["date"],
            y=ts_viz["roas_contract"],
            name="Contract ROAS",
            mode="markers+lines",
            marker=dict(size=4, color=ts_viz["roas_contract"], colorscale="RdYlGn", 
                       showscale=True, colorbar=dict(title="ROAS")),
            line=dict(width=1, color="lightgray")
        )
    )
    
    # Add break-even line
    fig4.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="red",
        annotation_text="Break-even (ROAS=1)",
        annotation_position="left"
    )
    
    fig4.update_layout(
        title="Contract ROAS Over Time (filtered: 0-20x)",
        xaxis_title="Date",
        yaxis_title="ROAS (x)",
        hovermode="closest",
        template="plotly_white",
        height=450
    )
    
    fig4.write_html(str(OUT_DIR / "figures" / "ts_roas.html"))
    fig4.write_image(str(OUT_DIR / "figures" / "ts_roas.png"), width=1200, height=550)


def plot_time_to_close_plotly(paid_ok: pd.DataFrame, stats: ClosingLagStats) -> None:
    """Create interactive time-to-close histogram"""
    if len(paid_ok) == 0:
        return
    
    p = paid_ok.copy()
    # Limit tail for readability
    p = p[p["lag_days"].between(-1, 120, inclusive="both")].copy()
    
    if len(p) == 0:
        return

    fig = go.Figure()
    
    fig.add_trace(
        go.Histogram(
            x=p["lag_days"],
            nbinsx=40,
            name="Time to Close",
            marker=dict(
                color="#4c78a8",
                line=dict(color="black", width=1)
            ),
            hovertemplate="Lag: %{x} days<br>Count: %{y}<extra></extra>"
        )
    )
    
    # Add median line
    if stats.lag_days_median:
        fig.add_vline(
            x=stats.lag_days_median,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Median: {stats.lag_days_median:.0f} days",
            annotation_position="top"
        )
    
    # Add p90 line
    if stats.lag_days_p90:
        fig.add_vline(
            x=stats.lag_days_p90,
            line_dash="dot",
            line_color="orange",
            annotation_text=f"P90: {stats.lag_days_p90:.0f} days",
            annotation_position="top right"
        )
    
    fig.update_layout(
        title=f"Time to Close Distribution (Coverage: {stats.coverage_pct:.1f}%)",
        xaxis_title="Days from Created to Closing",
        yaxis_title="Number of Deals",
        template="plotly_white",
        height=450,
        showlegend=False
    )
    
    fig.write_html(str(OUT_DIR / "figures" / "time_to_close_hist.html"))
    fig.write_image(str(OUT_DIR / "figures" / "time_to_close_hist.png"), width=1200, height=550)


def main() -> None:
    _ensure_dirs()
    deals, spend, calls = load_clean()

    print("[INFO] Building daily timeseries...")
    ts = build_daily_timeseries(deals, spend, calls)
    _save_table(ts, "timeseries_daily")
    
    print("[INFO] Generating timeseries visualizations...")
    plot_timeseries_plotly(ts)

    print("[INFO] Computing time-to-close...")
    paid_ok, stats = compute_time_to_close(deals)
    _save_table(paid_ok, "paid_time_to_close")
    _save_json(asdict(stats), "paid_time_to_close_stats")
    
    print("[INFO] Generating time-to-close visualization...")
    plot_time_to_close_plotly(paid_ok, stats)

    notes = {
        "closing_date_warning": "В данных у части paid сделок closing_date пустой; time-to-close считается только по тем, где обе даты есть.",
        "stage_history_warning": "Это снимок CRM, истории смены Stage нет; durations по этапам не считаем.",
        "moving_average_note": "7-day moving average используется для выявления трендов и снижения влияния ежедневных флуктуаций."
    }
    _save_json(notes, "notes")

    print("[OK] reports/time ready (tables + interactive plotly figures)")


if __name__ == "__main__":
    main()
