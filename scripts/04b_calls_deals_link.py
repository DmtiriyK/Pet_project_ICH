from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "calls_deals"


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)


def _save_table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _require_clean() -> None:
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")


def _link_calls_to_deals(calls: pd.DataFrame, deals: pd.DataFrame) -> pd.DataFrame:
    """
    Link calls to deals using contact_id_str.
    Note: This is approximate due to Excel ID corruption mentioned in docs.
    """
    calls_clean = calls[["contact_id_str", "call_start_time", "call_status", 
                         "call_type", "call_duration_minutes"]].copy()
    calls_clean = calls_clean[calls_clean["contact_id_str"].notna()].copy()
    
    deals_clean = deals[["deal_row_id", "contact_id_str", "stage", "is_paid", 
                         "created_time", "source", "product"]].copy()
    deals_clean = deals_clean[deals_clean["contact_id_str"].notna()].copy()
    
    # Group calls by contact
    calls_per_contact = (
        calls_clean
        .groupby("contact_id_str")
        .agg(
            calls_count=("contact_id_str", "size"),
            successful_calls=("call_status", lambda x: (x == "Successful").sum()),
            outgoing_calls=("call_type", lambda x: (x == "Outgoing").sum()),
            total_call_duration=("call_duration_minutes", "sum"),
        )
        .reset_index()
    )
    
    # Merge with deals
    merged = deals_clean.merge(calls_per_contact, on="contact_id_str", how="left")
    
    # Fill NaN for deals without calls
    merged["calls_count"] = merged["calls_count"].fillna(0).astype(int)
    merged["successful_calls"] = merged["successful_calls"].fillna(0).astype(int)
    merged["outgoing_calls"] = merged["outgoing_calls"].fillna(0).astype(int)
    merged["total_call_duration"] = merged["total_call_duration"].fillna(0)
    
    return merged


def main() -> None:
    _ensure_dirs()
    _require_clean()

    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")

    print("[INFO] Linking calls to deals...")
    linked = _link_calls_to_deals(calls, deals)
    
    # ===================================
    # ANALYSIS 1: Overall Coverage
    # ===================================
    total_deals = len(linked)
    deals_with_calls = (linked["calls_count"] > 0).sum()
    coverage_pct = (deals_with_calls / total_deals * 100).round(2)
    
    deals_with_successful = (linked["successful_calls"] > 0).sum()
    successful_coverage_pct = (deals_with_successful / total_deals * 100).round(2)
    
    coverage_stats = {
        "total_deals": int(total_deals),
        "deals_with_calls": int(deals_with_calls),
        "coverage_pct": float(coverage_pct),
        "deals_with_successful_calls": int(deals_with_successful),
        "successful_coverage_pct": float(successful_coverage_pct),
        "avg_calls_per_deal": float(linked["calls_count"].mean().round(2)),
        "median_calls_per_deal": float(linked["calls_count"].median()),
        "max_calls_per_deal": int(linked["calls_count"].max()),
    }
    _save_json(coverage_stats, "coverage_stats")
    
    # ===================================
    # ANALYSIS 2: Calls vs Paid Rate
    # ===================================
    print("[INFO] Analyzing calls vs paid rate...")
    
    # Bin calls into groups
    linked["calls_bin"] = pd.cut(
        linked["calls_count"],
        bins=[0, 1, 3, 5, 10, 100],
        labels=["0", "1-2", "3-4", "5-9", "10+"],
        include_lowest=True,
        right=False
    )
    
    calls_vs_paid = (
        linked.groupby("calls_bin", observed=True)
        .agg(
            deals_count=("deal_row_id", "size"),
            paid_count=("is_paid", lambda x: x.fillna(False).sum()),
        )
        .reset_index()
    )
    calls_vs_paid["paid_rate"] = (calls_vs_paid["paid_count"] / calls_vs_paid["deals_count"] * 100).round(2)
    calls_vs_paid["avg_calls"] = calls_vs_paid["calls_bin"].astype(str)
    
    _save_table(calls_vs_paid, "calls_vs_paid_rate")
    
    # ===================================
    # ANALYSIS 3: By Source
    # ===================================
    print("[INFO] Analyzing by source...")
    
    by_source = (
        linked.groupby("source", dropna=False)
        .agg(
            deals_count=("deal_row_id", "size"),
            paid_count=("is_paid", lambda x: x.fillna(False).sum()),
            avg_calls=("calls_count", "mean"),
            deals_with_calls=("calls_count", lambda x: (x > 0).sum()),
        )
        .reset_index()
    )
    by_source["paid_rate"] = (by_source["paid_count"] / by_source["deals_count"] * 100).round(2)
    by_source["coverage_pct"] = (by_source["deals_with_calls"] / by_source["deals_count"] * 100).round(2)
    by_source["avg_calls"] = by_source["avg_calls"].round(2)
    by_source = by_source.sort_values("deals_count", ascending=False)
    
    _save_table(by_source, "calls_coverage_by_source")
    
    # ===================================
    # ANALYSIS 4: Distribution of Calls per Deal
    # ===================================
    print("[INFO] Generating distribution table...")
    
    calls_dist = linked["calls_count"].value_counts().sort_index().reset_index()
    calls_dist.columns = ["calls_count", "deals_count"]
    calls_dist["share_pct"] = (calls_dist["deals_count"] / total_deals * 100).round(2)
    calls_dist["cumulative_pct"] = calls_dist["share_pct"].cumsum().round(2)
    
    _save_table(calls_dist.head(20), "calls_per_deal_distribution")
    
    # ===================================
    # VISUALIZATIONS
    # ===================================
    print("[INFO] Generating visualizations...")
    
    # 1. Calls vs Paid Rate
    fig, ax = plt.subplots(figsize=(10, 6))
    x_pos = np.arange(len(calls_vs_paid))
    
    ax2 = ax.twinx()
    
    # Bars for deal count
    bars = ax.bar(x_pos, calls_vs_paid["deals_count"], alpha=0.6, color='steelblue', label='Deals Count')
    
    # Line for paid rate
    line = ax2.plot(x_pos, calls_vs_paid["paid_rate"], color='darkred', marker='o', 
                    linewidth=2, markersize=8, label='Paid Rate %')
    
    ax.set_xlabel('Number of Calls', fontsize=12)
    ax.set_ylabel('Deals Count', fontsize=12, color='steelblue')
    ax2.set_ylabel('Paid Rate (%)', fontsize=12, color='darkred')
    ax.set_title('Calls per Deal vs Paid Rate', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(calls_vs_paid["calls_bin"])
    ax.tick_params(axis='y', labelcolor='steelblue')
    ax2.tick_params(axis='y', labelcolor='darkred')
    ax.grid(alpha=0.3, axis='y')
    
    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'figures' / 'calls_vs_paid_rate.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Distribution of calls per deal (histogram)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Filter for readability (top 90%)
    calls_to_plot = linked[linked["calls_count"] <= linked["calls_count"].quantile(0.9)]["calls_count"]
    
    ax.hist(calls_to_plot, bins=20, color='teal', alpha=0.7, edgecolor='black')
    ax.axvline(linked["calls_count"].median(), color='red', linestyle='--', 
               linewidth=2, label=f'Median: {linked["calls_count"].median():.1f}')
    ax.axvline(linked["calls_count"].mean(), color='orange', linestyle='--', 
               linewidth=2, label=f'Mean: {linked["calls_count"].mean():.1f}')
    
    ax.set_xlabel('Calls per Deal', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Calls per Deal (90th percentile)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'figures' / 'calls_per_deal_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. Coverage by source (top 10)
    top10_sources = by_source.head(10)
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    x_pos = np.arange(len(top10_sources))
    width = 0.35
    
    bars1 = ax.bar(x_pos - width/2, top10_sources["coverage_pct"], width, 
                   label='Call Coverage %', color='skyblue', edgecolor='black')
    bars2 = ax.bar(x_pos + width/2, top10_sources["paid_rate"], width, 
                   label='Paid Rate %', color='coral', edgecolor='black')
    
    ax.set_xlabel('Source', fontsize=12)
    ax.set_ylabel('Percentage (%)', fontsize=12)
    ax.set_title('Call Coverage & Paid Rate by Source (Top 10)', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(top10_sources["source"], rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'figures' / 'coverage_by_source.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 4. Scatter: avg_calls vs paid_rate by source
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Filter sources with at least 20 deals for meaningful analysis
    significant_sources = by_source[by_source["deals_count"] >= 20].copy()
    
    scatter = ax.scatter(
        significant_sources["avg_calls"], 
        significant_sources["paid_rate"],
        s=significant_sources["deals_count"],
        alpha=0.6,
        c=significant_sources["paid_rate"],
        cmap='RdYlGn',
        edgecolors='black'
    )
    
    # Add source labels for top sources
    for idx, row in significant_sources.head(5).iterrows():
        ax.annotate(
            row["source"],
            (row["avg_calls"], row["paid_rate"]),
            fontsize=9,
            alpha=0.8
        )
    
    ax.set_xlabel('Average Calls per Deal', fontsize=12)
    ax.set_ylabel('Paid Rate (%)', fontsize=12)
    ax.set_title('Avg Calls vs Paid Rate by Source (size = deals count)', 
                 fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Paid Rate (%)', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'figures' / 'scatter_calls_vs_paid.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # ===================================
    # NOTES
    # ===================================
    notes = {
        "methodology": "Calls linked to deals via contact_id_str. Note: Excel ID corruption means this is approximate.",
        "coverage_definition": "% of deals that have at least one call associated with them",
        "key_insight": f"{coverage_pct}% of deals have associated calls. Deals with more calls show different paid rates.",
        "caveat": "Correlation does not imply causation. More calls might indicate engaged leads OR struggling conversions.",
    }
    _save_json(notes, "notes")
    
    print(f"[OK] reports/calls_deals ready")
    print(f"     - Call coverage: {coverage_pct}% of deals have calls")
    print(f"     - Avg calls per deal: {coverage_stats['avg_calls_per_deal']}")


if __name__ == "__main__":
    main()
