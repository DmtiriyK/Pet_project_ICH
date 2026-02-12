"""
Сравнение Full vs Filtered datasets
Генерация comparison table для презентации и защиты
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "comparison"

# Reference данные
REFERENCE = {
    "T": 4572,
    "B": 843,
    "revenue": 3580815,
    "AC": 149523.45,
    "CPA_label": 8.27,  # это CPL!
}


def compute_metrics(deals: pd.DataFrame, spend: pd.DataFrame, name: str) -> dict:
    """Вычислить метрики для dataset"""
    T = len(deals)
    B = int(deals["is_paid"].fillna(False).sum())
    
    # Revenue только для paid
    paid_deals = deals[deals["is_paid"].fillna(False)]
    revenue_contract = paid_deals["revenue_contract"].fillna(0).sum()
    revenue_cash = paid_deals["revenue_cash"].fillna(0).sum()
    
    # Realistic revenue (weighted average) - только для filtered
    revenue_realistic = 0
    if "revenue_realistic" in deals.columns:
        revenue_realistic = paid_deals["revenue_realistic"].fillna(0).sum()
    
    AC = spend["spend"].fillna(0).sum()
    
    paid_rate = (B / T * 100) if T > 0 else 0
    CPL = AC / T if T > 0 else 0
    CPA = AC / B if B > 0 else 0
    ROAS_contract = revenue_contract / AC if AC > 0 else 0
    ROAS_cash = revenue_cash / AC if AC > 0 else 0
    ROAS_realistic = revenue_realistic / AC if AC > 0 and revenue_realistic > 0 else 0
    AOV = revenue_contract / B if B > 0 else 0
    AOV_realistic = revenue_realistic / B if B > 0 and revenue_realistic > 0 else 0
    
    return {
        "name": name,
        "T": T,
        "B": B,
        "revenue_contract": revenue_contract,
        "revenue_cash": revenue_cash,
        "revenue_realistic": revenue_realistic,
        "AC": AC,
        "paid_rate": paid_rate,
        "CPL": CPL,
        "CPA": CPA,
        "ROAS_contract": ROAS_contract,
        "ROAS_cash": ROAS_cash,
        "ROAS_realistic": ROAS_realistic,
        "AOV": AOV,
        "AOV_realistic": AOV_realistic,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("СРАВНЕНИЕ FULL vs FILTERED DATASETS")
    print("=" * 80)
    
    # Загрузка
    print("\n[1] Загрузка данных...")
    deals_full = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    deals_filtered = pd.read_parquet(CLEAN_DIR / "deals_filtered.parquet")
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")
    
    print(f"  Full:     {len(deals_full):,} deals")
    print(f"  Filtered: {len(deals_filtered):,} deals")
    
    # Метрики
    print("\n[2] Вычисление метрик...")
    m_full = compute_metrics(deals_full, spend, "Full (Ours)")
    m_filt = compute_metrics(deals_filtered, spend, "Filtered (Class)")
    
    # Reference
    ref_metrics = {
        "name": "Reference",
        "T": REFERENCE["T"],
        "B": REFERENCE["B"],
        "revenue_contract": REFERENCE["revenue"],
        "AC": REFERENCE["AC"],
        "CPL": REFERENCE["CPA_label"],  # это CPL на самом деле
        "CPA": REFERENCE["AC"] / REFERENCE["B"],
        "paid_rate": REFERENCE["B"] / REFERENCE["T"] * 100,
    }
    
    # Comparison table
    print("\n[3] Создание comparison table...")
    
    comparison = []
    
    metrics_to_compare = [
        ("Total Deals (T)", "T", 0),
        ("Paid Deals (B)", "B", 0),
        ("Revenue (realistic)", "revenue_realistic", 0),
        ("Revenue (contract)", "revenue_contract", 0),
        ("Revenue (cash)", "revenue_cash", 0),
        ("Spend (AC)", "AC", 2),
        ("Paid Rate (%)", "paid_rate", 2),
        ("CPL (€)", "CPL", 2),
        ("CPA (€)", "CPA", 2),
        ("ROAS (realistic)", "ROAS_realistic", 2),
        ("ROAS (contract)", "ROAS_contract", 2),
        ("AOV (realistic, €)", "AOV_realistic", 0),
        ("AOV (contract, €)", "AOV", 0),
    ]
    
    for label, key, decimals in metrics_to_compare:
        row = {"Metric": label}
        
        # Full
        if key in m_full:
            val_full = m_full[key]
            row["Full (Ours)"] = f"{val_full:,.{decimals}f}"
        else:
            row["Full (Ours)"] = "-"
        
        # Filtered
        if key in m_filt:
            val_filt = m_filt[key]
            row["Filtered (Class)"] = f"{val_filt:,.{decimals}f}"
            
            # Diff Full -> Filtered
            if key in m_full:
                diff = val_filt - val_full
                diff_pct = (diff / val_full * 100) if val_full != 0 else 0
                row["Diff"] = f"{diff_pct:+.1f}%"
            else:
                row["Diff"] = "-"
        else:
            row["Filtered (Class)"] = "-"
            row["Diff"] = "-"
        
        # Reference
        if key in ref_metrics:
            val_ref = ref_metrics[key]
            row["Reference"] = f"{val_ref:,.{decimals}f}"
            
            # Match Filtered -> Reference
            if key in m_filt:
                diff_ref = val_filt - val_ref
                diff_ref_pct = (diff_ref / val_ref * 100) if val_ref != 0 else 0
                row["Match"] = f"{diff_ref_pct:+.1f}%"
            else:
                row["Match"] = "-"
        else:
            row["Reference"] = "-"
            row["Match"] = "-"
        
        comparison.append(row)
    
    df_comp = pd.DataFrame(comparison)
    
    # Сохранение
    df_comp.to_csv(OUT_DIR / "full_vs_filtered.csv", index=False, encoding="utf-8")
    
    # Вывод
    print("\n" + "=" * 100)
    print("COMPARISON TABLE")
    print("=" * 100)
    print(df_comp.to_string(index=False))
    
    # Product-level comparison
    print("\n" + "=" * 100)
    print("PRODUCT-LEVEL COMPARISON")
    print("=" * 100)
    
    products_comp = []
    for product in ["Digital Marketing", "UX/UI Design", "Web Developer"]:
        # Full
        full_prod = deals_full[deals_full["product"] == product]
        t_full = len(full_prod)
        b_full = int(full_prod["is_paid"].fillna(False).sum())
        
        # Filtered
        filt_prod = deals_filtered[deals_filtered["product"] == product]
        t_filt = len(filt_prod)
        b_filt = int(filt_prod["is_paid"].fillna(False).sum())
        
        products_comp.append({
            "Product": product,
            "Full_T": t_full,
            "Full_B": b_full,
            "Filtered_T": t_filt,
            "Filtered_B": b_filt,
            "Same": "✅" if t_full == t_filt else "⚠️",
        })
    
    df_prod = pd.DataFrame(products_comp)
    df_prod.to_csv(OUT_DIR / "products_comparison.csv", index=False, encoding="utf-8")
    print(df_prod.to_string(index=False))
    
    # Summary JSON
    summary = {
        "full": m_full,
        "filtered": m_filt,
        "reference": ref_metrics,
        "insights": {
            "deals_removed": len(deals_full) - len(deals_filtered),
            "deals_removed_pct": (len(deals_full) - len(deals_filtered)) / len(deals_full) * 100,
            "paid_rate_change": m_filt["paid_rate"] - m_full["paid_rate"],
            "cpa_change": m_filt["CPA"] - m_full["CPA"],
            "closest_to_reference": "Filtered" if abs(m_filt["T"] - REFERENCE["T"]) < abs(m_full["T"] - REFERENCE["T"]) else "Full",
        }
    }
    
    with open(OUT_DIR / "comparison_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("INSIGHTS")
    print("=" * 80)
    print(f"📊 Filtered удалил {summary['insights']['deals_removed']:,} deals ({summary['insights']['deals_removed_pct']:.1f}%)")
    print(f"📈 Paid Rate: {m_full['paid_rate']:.2f}% → {m_filt['paid_rate']:.2f}% ({summary['insights']['paid_rate_change']:+.2f} pp)")
    print(f"💰 CPA: {m_full['CPA']:.2f}€ → {m_filt['CPA']:.2f}€ ({summary['insights']['cpa_change']:+.2f}€)")
    print(f"🎯 Closest to reference: {summary['insights']['closest_to_reference']}")
    
    print("\n✅ Saved:")
    print(f"  - {OUT_DIR / 'full_vs_filtered.csv'}")
    print(f"  - {OUT_DIR / 'products_comparison.csv'}")
    print(f"  - {OUT_DIR / 'comparison_summary.json'}")


if __name__ == "__main__":
    main()
