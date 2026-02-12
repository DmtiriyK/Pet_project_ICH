"""
Phase 2 Block 3.2: Correlation Analysis
Analyze correlations between numeric metrics (CPL, CPA, ROAS, paid_rate, etc.)
and generate heatmap visualization.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
REPORTS = ROOT / "reports" / "quality"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load clean deals and spend data."""
    deals = pd.read_csv(CLEAN / "deals.csv", parse_dates=["created_time", "closing_date"])
    spend = pd.read_csv(CLEAN / "spend.csv", parse_dates=["date"])
    return deals, spend


def compute_source_metrics(deals: pd.DataFrame, spend: pd.DataFrame) -> pd.DataFrame:
    """
    Compute key metrics by source for correlation analysis.
    
    Metrics:
    - CPL: cost per lead (spend / deals)
    - CPA: cost per acquisition (spend / paid_deals)
    - ROAS_cash: return on ad spend (cash)
    - ROAS_contract: return on ad spend (contract)
    - paid_rate: conversion rate (paid_deals / deals)
    - AOV_cash: average order value (cash)
    - AOV_contract: average order value (contract)
    - deals_count: total deals
    - paid_count: total paid deals
    - spend_total: total spend
    """
    # Aggregate deals by source
    deals_agg = deals.groupby("source").agg(
        deals_count=("deal_id_str", "size"),
        paid_count=("is_paid", "sum"),
        revenue_cash=("revenue_cash", "sum"),
        revenue_contract=("revenue_contract", "sum"),
    ).reset_index()
    
    # Aggregate spend by source
    spend_agg = spend.groupby("source").agg(
        spend_total=("spend", "sum"),
    ).reset_index()
    
    # Merge
    df = pd.merge(deals_agg, spend_agg, on="source", how="inner")
    
    # Compute metrics
    df["cpl"] = df["spend_total"] / df["deals_count"]
    df["cpa"] = df["spend_total"] / df["paid_count"]
    df["roas_cash"] = df["revenue_cash"] / df["spend_total"]
    df["roas_contract"] = df["revenue_contract"] / df["spend_total"]
    df["paid_rate"] = df["paid_count"] / df["deals_count"]
    df["aov_cash"] = df["revenue_cash"] / df["paid_count"]
    df["aov_contract"] = df["revenue_contract"] / df["paid_count"]
    
    # Replace inf/nan with 0 (edge cases where paid_count = 0)
    df = df.replace([float("inf"), float("-inf")], 0).fillna(0)
    
    return df


def plot_correlation_heatmap(df: pd.DataFrame, output_dir: Path) -> None:
    """Generate correlation heatmap for key metrics."""
    # Select numeric metrics for correlation
    metrics = [
        "cpl", "cpa", "roas_cash", "roas_contract", "paid_rate",
        "aov_cash", "aov_contract", "deals_count", "paid_count", "spend_total"
    ]
    
    corr_df = df[metrics].corr()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Heatmap
    sns.heatmap(
        corr_df,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    
    ax.set_title("Correlation Matrix: Key Metrics by Source", fontsize=16, weight="bold", pad=20)
    ax.set_xlabel("")
    ax.set_ylabel("")
    
    # Rotate labels
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    
    plt.tight_layout()
    
    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "correlation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    print(f"[OK] Correlation heatmap saved: {output_dir / 'correlation_heatmap.png'}")


def compute_key_correlations(df: pd.DataFrame, output_dir: Path) -> dict:
    """Compute and save key correlation insights."""
    metrics = [
        "cpl", "cpa", "roas_cash", "roas_contract", "paid_rate",
        "aov_cash", "aov_contract", "deals_count", "paid_count", "spend_total"
    ]
    
    corr_df = df[metrics].corr()
    
    # Extract key insights
    insights = {
        "cpl_vs_cpa": float(corr_df.loc["cpl", "cpa"]),
        "cpl_vs_roas_contract": float(corr_df.loc["cpl", "roas_contract"]),
        "paid_rate_vs_cpa": float(corr_df.loc["paid_rate", "cpa"]),
        "paid_rate_vs_roas_contract": float(corr_df.loc["paid_rate", "roas_contract"]),
        "aov_contract_vs_roas_contract": float(corr_df.loc["aov_contract", "roas_contract"]),
        "spend_total_vs_deals_count": float(corr_df.loc["spend_total", "deals_count"]),
        "cpa_vs_roas_contract": float(corr_df.loc["cpa", "roas_contract"]),
    }
    
    # Save as JSON
    output_file = output_dir / "correlation_insights.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Correlation insights saved: {output_file}")
    
    return insights


def generate_correlation_summary(insights: dict, output_dir: Path) -> None:
    """Generate human-readable summary of correlations."""
    summary = []
    
    summary.append("# Correlation Analysis Summary\n")
    summary.append("## Key Correlations (by Source)\n")
    
    summary.append(f"### CPL vs CPA: {insights['cpl_vs_cpa']:.3f}")
    summary.append("- Strong positive correlation expected (higher CPL → higher CPA).\n")
    
    summary.append(f"### CPL vs ROAS (Contract): {insights['cpl_vs_roas_contract']:.3f}")
    summary.append("- Negative correlation ideal (lower CPL → higher ROAS).\n")
    
    summary.append(f"### Paid Rate vs CPA: {insights['paid_rate_vs_cpa']:.3f}")
    summary.append("- Strong negative correlation expected (higher conversion → lower CPA).\n")
    
    summary.append(f"### Paid Rate vs ROAS (Contract): {insights['paid_rate_vs_roas_contract']:.3f}")
    summary.append("- Positive correlation ideal (higher conversion → higher ROAS).\n")
    
    summary.append(f"### AOV (Contract) vs ROAS (Contract): {insights['aov_contract_vs_roas_contract']:.3f}")
    summary.append("- Strong positive correlation expected (higher AOV → higher ROAS).\n")
    
    summary.append(f"### CPA vs ROAS (Contract): {insights['cpa_vs_roas_contract']:.3f}")
    summary.append("- Strong negative correlation expected (lower CPA → higher ROAS).\n")
    
    summary.append("\n## Interpretation")
    summary.append("- **High positive**: CPL↔CPA, AOV↔ROAS")
    summary.append("- **High negative**: Paid_Rate↔CPA, CPA↔ROAS")
    summary.append("- **Growth levers**: Focus on sources with high Paid_Rate and low CPL to maximize ROAS.")
    
    # Save
    summary_file = output_dir / "correlation_summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    
    print(f"[OK] Correlation summary saved: {summary_file}")


def main() -> None:
    print("[INFO] Loading data...")
    deals, spend = load_data()
    
    print("[INFO] Computing source-level metrics...")
    metrics_df = compute_source_metrics(deals, spend)
    
    # Save metrics table
    REPORTS.mkdir(parents=True, exist_ok=True)
    tables_dir = REPORTS / "tables"
    tables_dir.mkdir(exist_ok=True)
    metrics_df.to_csv(tables_dir / "source_metrics_correlation.csv", index=False)
    print(f"[OK] Source metrics table saved: {tables_dir / 'source_metrics_correlation.csv'}")
    
    print("[INFO] Generating correlation heatmap...")
    figures_dir = REPORTS / "figures"
    plot_correlation_heatmap(metrics_df, figures_dir)
    
    print("[INFO] Computing key correlation insights...")
    insights = compute_key_correlations(metrics_df, REPORTS)
    
    print("[INFO] Generating correlation summary...")
    generate_correlation_summary(insights, REPORTS)
    
    print("\n[OK] Correlation analysis complete!")
    print(f"    - Heatmap: {figures_dir / 'correlation_heatmap.png'}")
    print(f"    - Insights: {REPORTS / 'correlation_insights.json'}")
    print(f"    - Summary: {REPORTS / 'correlation_summary.md'}")


if __name__ == "__main__":
    main()
