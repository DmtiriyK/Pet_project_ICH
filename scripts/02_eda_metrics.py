from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "eda"


@dataclass(frozen=True)
class OverallMetrics:
    spend_total: float
    deals_total: int
    paid_deals: int
    paid_rate: float
    revenue_cash_total: float
    revenue_contract_total: float


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)


def _save_table(df: pd.DataFrame, name: str) -> None:
    path_csv = OUT_DIR / "tables" / f"{name}.csv"
    df.to_csv(path_csv, index=False, encoding="utf-8")


def _save_json(obj: object, name: str) -> None:
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _format_axes(ax: plt.Axes, *, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)


def load_clean() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    contacts = pd.read_parquet(CLEAN_DIR / "contacts.parquet")
    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")
    return contacts, calls, deals, spend


def compute_overall(deals: pd.DataFrame, spend: pd.DataFrame) -> OverallMetrics:
    spend_total = float(pd.to_numeric(spend["spend"], errors="coerce").fillna(0).sum())
    deals_total = int(len(deals))
    paid_deals = int(deals["is_paid"].fillna(False).sum())
    paid_rate = float(paid_deals / deals_total) if deals_total else float("nan")
    revenue_cash_total = float(pd.to_numeric(deals["revenue_cash"], errors="coerce").fillna(0).sum())
    revenue_contract_total = float(pd.to_numeric(deals["revenue_contract"], errors="coerce").fillna(0).sum())
    return OverallMetrics(
        spend_total=spend_total,
        deals_total=deals_total,
        paid_deals=paid_deals,
        paid_rate=paid_rate,
        revenue_cash_total=revenue_cash_total,
        revenue_contract_total=revenue_contract_total,
    )


def stage_funnel(deals: pd.DataFrame) -> pd.DataFrame:
    out = (
        deals.assign(stage=deals["stage"].fillna("NA"))
        .groupby("stage", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
        )
        .reset_index()
    )
    out["paid_rate"] = out["paid_deals"] / out["deals"].replace(0, np.nan)
    return out.sort_values("deals", ascending=False)


def time_series(deals: pd.DataFrame, spend: pd.DataFrame, calls: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["created_date"] = pd.to_datetime(d["created_time"], errors="coerce").dt.date
    deals_daily = (
        d.groupby("created_date", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
        .rename(columns={"created_date": "date"})
    )

    s = spend.copy()
    # spend.date уже date (не datetime)
    spend_daily = s.groupby("date", dropna=False).agg(spend=("spend", "sum")).reset_index()

    c = calls.copy()
    c["date"] = pd.to_datetime(c["call_start_time"], errors="coerce").dt.date
    calls_daily = c.groupby("date", dropna=False).agg(calls=("call_id", "size")).reset_index()

    ts = deals_daily.merge(spend_daily, on="date", how="outer").merge(calls_daily, on="date", how="outer")
    for col in ["deals", "paid_deals", "revenue_cash", "revenue_contract", "spend", "calls"]:
        ts[col] = pd.to_numeric(ts[col], errors="coerce").fillna(0)
    ts = ts.sort_values("date")
    return ts


def ads_performance(deals: pd.DataFrame, spend: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = deals.copy()
    d["source"] = d["source"].fillna("NA")
    d["campaign"] = d["campaign"].fillna("NA")

    by_sc = (
        d.groupby(["source", "campaign"], dropna=False)
        .agg(
            leads=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )

    s = spend.copy()
    s["source"] = s["source"].fillna("NA")
    s["campaign"] = s["campaign"].fillna("NA")

    spend_sc = s.groupby(["source", "campaign"], dropna=False).agg(spend=("spend", "sum")).reset_index()

    m = spend_sc.merge(by_sc, on=["source", "campaign"], how="outer")
    for col in ["spend", "leads", "paid_deals", "revenue_cash", "revenue_contract"]:
        m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0)

    m["cpl"] = m["spend"] / m["leads"].replace(0, np.nan)
    m["cpa"] = m["spend"] / m["paid_deals"].replace(0, np.nan)
    m["cash_roas"] = m["revenue_cash"] / m["spend"].replace(0, np.nan)
    m["contract_roas"] = m["revenue_contract"] / m["spend"].replace(0, np.nan)

    by_source = (
        m.groupby("source", dropna=False)
        .agg(
            spend=("spend", "sum"),
            leads=("leads", "sum"),
            paid_deals=("paid_deals", "sum"),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    by_source["cpl"] = by_source["spend"] / by_source["leads"].replace(0, np.nan)
    by_source["cpa"] = by_source["spend"] / by_source["paid_deals"].replace(0, np.nan)
    by_source["cash_roas"] = by_source["revenue_cash"] / by_source["spend"].replace(0, np.nan)
    by_source["contract_roas"] = by_source["revenue_contract"] / by_source["spend"].replace(0, np.nan)

    return by_source.sort_values("spend", ascending=False), m.sort_values("spend", ascending=False)


def sales_performance(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["deal_owner_name"] = d["deal_owner_name"].fillna("NA")
    out = (
        d.groupby("deal_owner_name", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
            paid_rate=("is_paid", lambda s: float(s.fillna(False).mean())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
            sla_minutes_median=("sla_minutes", "median"),
        )
        .reset_index()
    )
    out["cash_per_paid"] = out["revenue_cash"] / out["paid_deals"].replace(0, np.nan)
    out["contract_per_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    return out.sort_values("revenue_contract", ascending=False)


def product_unit_econ(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["product"] = d["product"].fillna("NA")
    out = (
        d.groupby("product", dropna=False)
        .agg(
            leads=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda s: int(s.fillna(False).sum())),
            paid_rate=("is_paid", lambda s: float(s.fillna(False).mean())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )
    out["cash_aov_paid"] = out["revenue_cash"] / out["paid_deals"].replace(0, np.nan)
    out["contract_aov_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    return out.sort_values("revenue_contract", ascending=False)


def product_unit_econ_known_only(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d["product"] = d["product"].fillna("NA")
    d = d[d["product"].ne("NA")].copy()
    if len(d) == 0:
        return pd.DataFrame(
            columns=[
                "product",
                "leads",
                "paid_deals",
                "paid_rate",
                "revenue_cash",
                "revenue_contract",
                "cash_aov_paid",
                "contract_aov_paid",
            ]
        )
    return product_unit_econ(d)


def product_unit_econ_paid_only(deals: pd.DataFrame) -> pd.DataFrame:
    d = deals.copy()
    d = d[d["is_paid"].fillna(False)].copy()
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
    out["cash_aov_paid"] = out["revenue_cash"] / out["paid_deals"].replace(0, np.nan)
    out["contract_aov_paid"] = out["revenue_contract"] / out["paid_deals"].replace(0, np.nan)
    return out.sort_values("revenue_contract", ascending=False)


def plot_funnel(stage_df: pd.DataFrame) -> None:
    top = stage_df.head(12).copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top, x="deals", y="stage", ax=ax, color="#4c78a8")
    _format_axes(ax, title="Deals by Stage (top 12)", xlabel="Deals", ylabel="Stage")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "stage_funnel_top12.png", dpi=160)
    plt.close(fig)


def plot_time_series(ts: pd.DataFrame) -> None:
    ts2 = ts.copy()
    ts2 = ts2[ts2["date"].notna()].copy()
    ts2["date"] = pd.to_datetime(ts2["date"])

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(ts2["date"], ts2["deals"], label="Deals created", linewidth=1.5)
    ax.plot(ts2["date"], ts2["paid_deals"], label="Paid deals (by stage flag)", linewidth=1.5)
    _format_axes(ax, title="Deals and Paid Deals over Time", xlabel="Date", ylabel="Count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "deals_paid_timeseries.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(ts2["date"], ts2["spend"], label="Spend", linewidth=1.5)
    ax2 = ax.twinx()
    ax2.plot(ts2["date"], ts2["paid_deals"], label="Paid deals", color="#f58518", linewidth=1.5)
    ax.set_title("Spend vs Paid Deals over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Spend")
    ax2.set_ylabel("Paid deals")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "spend_vs_paid_timeseries.png", dpi=160)
    plt.close(fig)


def plot_ads_sources(source_df: pd.DataFrame) -> None:
    top = source_df.sort_values("spend", ascending=False).head(12).copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top, x="spend", y="source", ax=ax, color="#54a24b")
    _format_axes(ax, title="Spend by Source (top 12)", xlabel="Spend", ylabel="Source")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "spend_by_source_top12.png", dpi=160)
    plt.close(fig)

    top2 = source_df.copy()
    top2 = top2[(top2["spend"] >= 1000) & (top2["paid_deals"] >= 3)].sort_values("contract_roas", ascending=False).head(12)
    if len(top2):
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=top2, x="contract_roas", y="source", ax=ax, color="#e45756")
        _format_axes(ax, title="Contract ROAS by Source (spend>=1000, paid>=3)", xlabel="ROAS (contract)", ylabel="Source")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "figures" / "contract_roas_by_source.png", dpi=160)
        plt.close(fig)


def plot_sales_owners(owner_df: pd.DataFrame) -> None:
    top = owner_df.sort_values("paid_rate", ascending=False).head(15).copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=top, x="paid_rate", y="deal_owner_name", ax=ax, color="#f58518")
    _format_axes(ax, title="Paid Rate by Deal Owner (top 15)", xlabel="Paid rate", ylabel="Owner")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "paid_rate_by_owner_top15.png", dpi=160)
    plt.close(fig)


def plot_products(product_df: pd.DataFrame) -> None:
    top = product_df.sort_values("revenue_contract", ascending=False).head(15).copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=top, x="revenue_contract", y="product", ax=ax, color="#72b7b2")
    _format_axes(ax, title="Contract Revenue by Product (top 15)", xlabel="Revenue (contract)", ylabel="Product")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "revenue_contract_by_product_top15.png", dpi=160)
    plt.close(fig)


def main() -> None:
    _ensure_dirs()

    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")

    contacts, calls, deals, spend = load_clean()

    overall = compute_overall(deals, spend)
    _save_json(asdict(overall), "metrics_overall")

    funnel = stage_funnel(deals)
    _save_table(funnel, "stage_funnel")

    ts = time_series(deals, spend, calls)
    _save_table(ts, "timeseries_daily")

    by_source, by_campaign = ads_performance(deals, spend)
    _save_table(by_source, "ads_by_source")
    _save_table(by_campaign, "ads_by_source_campaign")

    owners = sales_performance(deals)
    _save_table(owners, "sales_by_owner")

    products = product_unit_econ(deals)
    _save_table(products, "product_unit_econ")
    _save_table(product_unit_econ_known_only(deals), "product_unit_econ_known_only")
    _save_table(product_unit_econ_paid_only(deals), "product_unit_econ_paid_only")

    plot_funnel(funnel)
    plot_time_series(ts)
    plot_ads_sources(by_source)
    plot_sales_owners(owners)
    plot_products(products)

    print("OK: reports/eda ready")


if __name__ == "__main__":
    main()
