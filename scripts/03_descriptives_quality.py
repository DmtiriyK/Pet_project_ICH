from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "quality"


@dataclass(frozen=True)
class TableShape:
    rows: int
    cols: int


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)


def _save_table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _missingness(df: pd.DataFrame) -> pd.DataFrame:
    miss_cnt = df.isna().sum()
    miss_pct = (df.isna().mean() * 100).round(2)
    out = (
        pd.DataFrame({"column": df.columns, "missing_count": miss_cnt.values, "missing_pct": miss_pct.values})
        .sort_values(["missing_pct", "missing_count"], ascending=False)
        .reset_index(drop=True)
    )
    return out


def _numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for col in cols:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        
        # Calculate mode - take first if multiple modes exist
        mode_val = np.nan
        if s.notna().any():
            mode_series = s.mode()
            if len(mode_series) > 0:
                mode_val = float(mode_series.iloc[0])
        
        rows.append(
            {
                "column": col,
                "count": int(s.notna().sum()),
                "missing_pct": float((s.isna().mean() * 100).round(2)),
                "mean": float(s.mean()) if s.notna().any() else np.nan,
                "median": float(s.median()) if s.notna().any() else np.nan,
                "mode": mode_val,
                "std": float(s.std()) if s.notna().any() else np.nan,
                "min": float(s.min()) if s.notna().any() else np.nan,
                "p25": float(s.quantile(0.25)) if s.notna().any() else np.nan,
                "p75": float(s.quantile(0.75)) if s.notna().any() else np.nan,
                "p90": float(s.quantile(0.90)) if s.notna().any() else np.nan,
                "max": float(s.max()) if s.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("missing_pct", ascending=True).reset_index(drop=True)


def _top_values(df: pd.DataFrame, col: str, top_n: int = 30) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(columns=[col, "count", "share_pct"])
    vc = df[col].fillna("NA").astype(str).value_counts(dropna=False).head(top_n)
    out = vc.reset_index()
    out.columns = [col, "count"]
    out["share_pct"] = (out["count"] / len(df) * 100).round(2)
    return out


def _plot_histogram_with_kde(df: pd.DataFrame, col: str, title: str, output_path: Path) -> None:
    """Plot histogram with KDE overlay"""
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    
    if len(s) == 0:
        print(f"[SKIP] {col}: no data")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Histogram
    ax.hist(s, bins=30, alpha=0.6, color='steelblue', edgecolor='black', density=True, label='Histogram')
    
    # KDE
    try:
        s.plot.kde(ax=ax, color='darkred', linewidth=2, label='KDE')
    except:
        pass  # Skip KDE if data is unsuitable
    
    ax.set_xlabel(col, fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def _plot_boxplot(df: pd.DataFrame, col: str, title: str, output_path: Path) -> None:
    """Plot boxplot"""
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    
    if len(s) == 0:
        print(f"[SKIP] {col}: no data")
        return
    
    fig, ax = plt.subplots(figsize=(10, 4))
    
    bp = ax.boxplot([s], vert=False, patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('lightblue')
    bp['boxes'][0].set_edgecolor('black')
    bp['medians'][0].set_color('red')
    bp['medians'][0].set_linewidth(2)
    
    ax.set_xlabel(col, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3, axis='x')
    ax.set_yticklabels([col])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def _plot_horizontal_barplot(df: pd.DataFrame, col: str, title: str, output_path: Path, top_n: int = 15) -> None:
    """Plot horizontal barplot for categorical variables"""
    vc = df[col].fillna("NA").astype(str).value_counts(dropna=False).head(top_n)
    
    if len(vc) == 0:
        print(f"[SKIP] {col}: no data")
        return
    
    fig, ax = plt.subplots(figsize=(10, max(6, len(vc) * 0.4)))
    
    # Sort by value for better readability
    vc_sorted = vc.sort_values()
    
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(vc_sorted)))
    bars = ax.barh(range(len(vc_sorted)), vc_sorted.values, color=colors, edgecolor='black')
    
    ax.set_yticks(range(len(vc_sorted)))
    ax.set_yticklabels(vc_sorted.index, fontsize=10)
    ax.set_xlabel('Count', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3, axis='x')
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, vc_sorted.values)):
        ax.text(val + max(vc_sorted.values) * 0.01, i, f'{int(val)}', 
                va='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def _plot_missingness_heatmap(tables: dict[str, pd.DataFrame], output_path: Path) -> None:
    """Plot missingness heatmap for all tables"""
    miss_data = []
    
    for name, df in tables.items():
        miss_pct = (df.isna().mean() * 100).round(1)
        for col, pct in miss_pct.items():
            miss_data.append({'table': name, 'column': col, 'missing_pct': pct})
    
    miss_df = pd.DataFrame(miss_data)
    
    # Pivot for heatmap
    pivot = miss_df.pivot(index='column', columns='table', values='missing_pct').fillna(0)
    
    # Filter: show only columns with any missingness
    pivot = pivot[pivot.sum(axis=1) > 0]
    
    if pivot.empty:
        print("[INFO] No missing values to plot")
        return
    
    fig, ax = plt.subplots(figsize=(10, max(8, len(pivot) * 0.3)))
    
    sns.heatmap(
        pivot, 
        annot=True, 
        fmt='.1f', 
        cmap='YlOrRd', 
        cbar_kws={'label': 'Missing %'},
        linewidths=0.5,
        ax=ax
    )
    
    ax.set_title('Missingness Heatmap (% missing)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Table', fontsize=12)
    ax.set_ylabel('Column', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def load_clean() -> dict[str, pd.DataFrame]:
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")
    return {
        "contacts": pd.read_parquet(CLEAN_DIR / "contacts.parquet"),
        "calls": pd.read_parquet(CLEAN_DIR / "calls.parquet"),
        "deals": pd.read_parquet(CLEAN_DIR / "deals.parquet"),
        "spend": pd.read_parquet(CLEAN_DIR / "spend.parquet"),
    }


def main() -> None:
    _ensure_dirs()
    tables = load_clean()

    shapes = {name: asdict(TableShape(rows=len(df), cols=int(df.shape[1]))) for name, df in tables.items()}
    _save_json(shapes, "shapes")

    for name, df in tables.items():
        _save_table(_missingness(df), f"{name}_missingness")

    deals = tables["deals"]
    spend = tables["spend"]
    calls = tables["calls"]

    # Deals numeric summaries
    deals_numeric = _numeric_summary(
        deals,
        [
            "initial_amount_paid",
            "offer_total_amount",
            "revenue_cash",
            "revenue_contract",
            "course_duration",
            "months_of_study",
            "sla_minutes",
        ],
    )
    _save_table(deals_numeric, "deals_numeric_summary")

    # Deals categorical top values
    for col in [
        "stage",
        "quality",
        "source",
        "campaign",
        "payment_type",
        "product",
        "education_type",
        "city",
        "level_of_deutsch",
        "deal_owner_name",
        "lost_reason",
    ]:
        _save_table(_top_values(deals, col), f"deals_top_{col}")

    # Spend numeric summaries
    spend_numeric = _numeric_summary(spend, ["spend", "clicks", "impressions"])
    _save_table(spend_numeric, "spend_numeric_summary")
    _save_table(_top_values(spend, "source"), "spend_top_source")
    _save_table(_top_values(spend, "campaign"), "spend_top_campaign")

    # Calls numeric summaries
    calls_numeric = _numeric_summary(calls, ["call_duration_seconds", "call_duration_minutes"])
    _save_table(calls_numeric, "calls_numeric_summary")
    for col in ["call_status", "call_type", "outgoing_call_status", "scheduled_in_crm", "call_owner_name"]:
        _save_table(_top_values(calls, col), f"calls_top_{col}")

    # Notes
    notes = {
        "paid_definition": "deals.is_paid == True (Stage == 'Payment Done', case-insensitive)",
        "id_caveat": "contact_id_str/contact_id15 получены из Excel-чисел; это не гарантирует точный джойн.",
        "missing_values_policy": "Пропуски не заполнялись массово; дальнейшая обработка — по смыслу и по срезам.",
    }
    _save_json(notes, "notes")

    # ============================================
    # VISUALIZATIONS
    # ============================================
    print("[INFO] Generating visualizations...")
    
    # 1. Histograms with KDE for key numeric variables
    print("[INFO] - Histograms with KDE...")
    _plot_histogram_with_kde(
        deals, 'revenue_cash', 
        'Distribution of Revenue (Cash)', 
        OUT_DIR / 'figures' / 'hist_revenue_cash.png'
    )
    _plot_histogram_with_kde(
        deals, 'revenue_contract', 
        'Distribution of Revenue (Contract)', 
        OUT_DIR / 'figures' / 'hist_revenue_contract.png'
    )
    _plot_histogram_with_kde(
        deals, 'sla_minutes', 
        'Distribution of SLA Minutes', 
        OUT_DIR / 'figures' / 'hist_sla_minutes.png'
    )
    
    # 2. Boxplots
    print("[INFO] - Boxplots...")
    _plot_boxplot(
        deals, 'revenue_cash', 
        'Boxplot: Revenue (Cash)', 
        OUT_DIR / 'figures' / 'box_revenue_cash.png'
    )
    _plot_boxplot(
        deals, 'revenue_contract', 
        'Boxplot: Revenue (Contract)', 
        OUT_DIR / 'figures' / 'box_revenue_contract.png'
    )
    _plot_boxplot(
        deals, 'sla_minutes', 
        'Boxplot: SLA Minutes', 
        OUT_DIR / 'figures' / 'box_sla_minutes.png'
    )
    
    # 3. Horizontal barplots for key categorical variables
    print("[INFO] - Categorical barplots...")
    _plot_horizontal_barplot(
        deals, 'stage', 
        'Deals by Stage', 
        OUT_DIR / 'figures' / 'bar_stage.png'
    )
    _plot_horizontal_barplot(
        deals, 'source', 
        'Deals by Source', 
        OUT_DIR / 'figures' / 'bar_source.png'
    )
    _plot_horizontal_barplot(
        deals, 'product', 
        'Deals by Product', 
        OUT_DIR / 'figures' / 'bar_product.png'
    )
    _plot_horizontal_barplot(
        deals, 'quality', 
        'Deals by Quality', 
        OUT_DIR / 'figures' / 'bar_quality.png'
    )
    _plot_horizontal_barplot(
        deals, 'payment_type', 
        'Deals by Payment Type', 
        OUT_DIR / 'figures' / 'bar_payment_type.png'
    )
    _plot_horizontal_barplot(
        deals, 'city', 
        'Deals by City', 
        OUT_DIR / 'figures' / 'bar_city.png'
    )
    _plot_horizontal_barplot(
        deals, 'level_of_deutsch', 
        'Deals by Level of Deutsch', 
        OUT_DIR / 'figures' / 'bar_level_of_deutsch.png'
    )
    
    # 4. Missingness heatmap
    print("[INFO] - Missingness heatmap...")
    _plot_missingness_heatmap(
        tables, 
        OUT_DIR / 'figures' / 'missingness_heatmap.png'
    )
    
    print("[OK] reports/quality ready (tables + figures)")


if __name__ == "__main__":
    main()

