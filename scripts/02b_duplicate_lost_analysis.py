from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "eda"


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def main() -> None:
    _ensure_dirs()
    
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")
    
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    
    # ============================================
    # DUPLICATE LOST ANALYSIS
    # ============================================
    print("[INFO] Analyzing duplicate lost deals...")
    
    # Count duplicates
    total_deals = len(deals)
    duplicate_lost_count = int(deals["is_duplicate_lost"].fillna(False).sum())
    duplicate_pct = round(duplicate_lost_count / total_deals * 100, 2)
    
    # Breakdown by stage
    lost_stage_mask = deals["stage"].fillna("").str.lower().str.contains("lost")
    total_lost = lost_stage_mask.sum()
    
    duplicate_among_lost = int(
        deals[lost_stage_mask & deals["is_duplicate_lost"].fillna(False)].shape[0]
    )
    duplicate_among_lost_pct = round(duplicate_among_lost / total_lost * 100, 2) if total_lost > 0 else 0
    
    real_lost = total_lost - duplicate_among_lost
    real_lost_pct = round(real_lost / total_deals * 100, 2)
    
    # Metrics comparison: with vs without duplicates
    paid_deals = int(deals["is_paid"].fillna(False).sum())
    
    # WITH duplicates (current naive approach)
    naive_paid_rate = round(paid_deals / total_deals * 100, 2)
    
    # WITHOUT duplicates (correct approach)
    real_deals = total_deals - duplicate_lost_count
    corrected_paid_rate = round(paid_deals / real_deals * 100, 2)
    
    impact_on_paid_rate = round(corrected_paid_rate - naive_paid_rate, 2)
    
    # Summary stats
    duplicate_stats = {
        "total_deals": int(total_deals),
        "duplicate_lost_count": int(duplicate_lost_count),
        "duplicate_pct": float(duplicate_pct),
        "total_lost_stage": int(total_lost),
        "duplicate_among_lost": int(duplicate_among_lost),
        "duplicate_among_lost_pct": float(duplicate_among_lost_pct),
        "real_lost": int(real_lost),
        "real_lost_pct": float(real_lost_pct),
        "paid_deals": int(paid_deals),
        "naive_paid_rate_pct": float(naive_paid_rate),
        "corrected_paid_rate_pct": float(corrected_paid_rate),
        "impact_on_paid_rate_pp": float(impact_on_paid_rate),
        "interpretation": (
            f"Excluding {duplicate_lost_count} duplicate lost deals increases "
            f"paid rate from {naive_paid_rate}% to {corrected_paid_rate}% "
            f"(+{impact_on_paid_rate:.2f} pp). "
            f"These duplicates represent {duplicate_among_lost_pct}% of all 'Lost' stage deals."
        )
    }
    
    _save_json(duplicate_stats, "duplicate_lost_impact")
    
    # Breakdown by source
    print("[INFO] Analyzing duplicates by source...")
    
    by_source = (
        deals.groupby("source", dropna=False)
        .agg(
            total_deals=("deal_row_id", "size"),
            duplicate_lost=("is_duplicate_lost", lambda x: int(x.fillna(False).sum())),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
        )
        .reset_index()
    )
    
    by_source["duplicate_pct"] = (by_source["duplicate_lost"] / by_source["total_deals"] * 100).round(2)
    by_source["real_deals"] = by_source["total_deals"] - by_source["duplicate_lost"]
    by_source["naive_paid_rate"] = (by_source["paid_deals"] / by_source["total_deals"] * 100).round(2)
    by_source["corrected_paid_rate"] = (
        by_source["paid_deals"] / by_source["real_deals"].replace(0, pd.NA) * 100
    ).round(2)
    by_source["impact_pp"] = (by_source["corrected_paid_rate"] - by_source["naive_paid_rate"]).round(2)
    
    by_source = by_source.sort_values("total_deals", ascending=False)
    
    _save_table(by_source, "duplicate_lost_by_source")
    
    # Breakdown by lost reason
    print("[INFO] Analyzing lost reasons...")
    
    lost_deals = deals[lost_stage_mask].copy()
    
    lost_reasons = (
        lost_deals.groupby("lost_reason", dropna=False)
        .agg(
            count=("deal_row_id", "size"),
            is_duplicate=("is_duplicate_lost", lambda x: int(x.fillna(False).sum())),
        )
        .reset_index()
    )
    
    lost_reasons["duplicate_pct"] = (lost_reasons["is_duplicate"] / lost_reasons["count"] * 100).round(2)
    lost_reasons = lost_reasons.sort_values("count", ascending=False)
    
    _save_table(lost_reasons, "lost_reason_breakdown")
    
    print(f"[OK] Duplicate lost analysis complete")
    print(f"     - Total duplicates: {duplicate_lost_count} ({duplicate_pct}%)")
    print(f"     - Impact on paid rate: +{impact_on_paid_rate:.2f} pp when excluded")
    print(f"     - Duplicates among 'Lost' deals: {duplicate_among_lost_pct}%")


if __name__ == "__main__":
    main()
