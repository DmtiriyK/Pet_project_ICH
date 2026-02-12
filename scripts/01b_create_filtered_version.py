"""
Создание filtered версии данных (как делал класс)
Тестирование разных сценариев фильтрации и выбор best match к reference
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"


# Reference данные из скриншота
REFERENCE = {
    "T": 4572,
    "B": 843,
    "revenue": 3580815,
    "products": {
        "Digital Marketing": {"T": 2897, "B": 469, "revenue": 2262490},
        "UX/UI Design": {"T": 1170, "B": 226, "revenue": 951645},
        "Web Developer": {"T": 505, "B": 135, "revenue": 366680},
    },
}


def test_scenario(deals: pd.DataFrame, name: str, filter_func) -> dict:
    """Тестировать сценарий фильтрации и вернуть метрики"""
    filtered = filter_func(deals.copy())
    
    T = len(filtered)
    B = int(filtered["is_paid"].fillna(False).sum())
    revenue = filtered["revenue_contract"].fillna(0).sum()
    
    # По продуктам
    products = {}
    for prod in ["Digital Marketing", "UX/UI Design", "Web Developer"]:
        prod_df = filtered[filtered["product"] == prod]
        if len(prod_df) > 0:
            products[prod] = {
                "T": len(prod_df),
                "B": int(prod_df["is_paid"].fillna(False).sum()),
                "revenue": prod_df["revenue_contract"].fillna(0).sum(),
            }
    
    # Match score
    t_diff = abs(T - REFERENCE["T"])
    b_diff = abs(B - REFERENCE["B"])
    match_score = 1000 - t_diff - b_diff * 2  # B важнее
    
    return {
        "name": name,
        "T": T,
        "B": B,
        "revenue": revenue,
        "products": products,
        "match_score": match_score,
        "t_diff": t_diff,
        "b_diff": b_diff,
    }


def main() -> None:
    print("=" * 80)
    print("СОЗДАНИЕ FILTERED DATASET (CLASS-LIKE APPROACH)")
    print("=" * 80)
    
    # Загрузка
    print("\n[1] Загрузка данных...")
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")
    contacts = pd.read_parquet(CLEAN_DIR / "contacts.parquet")
    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    
    print(f"  Loaded: {len(deals):,} deals, {len(spend):,} spend records")
    
    # Scenarios
    print("\n[2] Тестирование сценариев фильтрации...")
    
    scenarios = {
        "A_known_products": lambda df: df[
            (df["product"].notna()) & (df["product"] != "NA")
        ],
        "B_known_products_no_dup_lost": lambda df: df[
            (df["product"].notna()) & 
            (df["product"] != "NA") & 
            (~df["is_duplicate_lost"])
        ],
        "C_known_products_active": lambda df: df[
            (df["product"].notna()) & 
            (df["product"] != "NA") &
            (~df["stage"].str.contains("Lost|Delayed", case=False, na=False))
        ],
        "D_known_products_quality": lambda df: df[
            (df["product"].notna()) & 
            (df["product"] != "NA") &
            (~df["is_duplicate_lost"]) &
            (df["quality"].notna())
        ],
        "E_main_products_only": lambda df: df[
            df["product"].isin(["Digital Marketing", "UX/UI Design", "Web Developer"])
        ],
    }
    
    results = []
    for name, func in scenarios.items():
        result = test_scenario(deals, name, func)
        results.append(result)
        
        print(f"\n  {name}:")
        print(f"    Deals: {result['T']:,} (diff: {result['t_diff']:+,})")
        print(f"    Paid:  {result['B']:,} (diff: {result['b_diff']:+,})")
        print(f"    Revenue: {result['revenue']:,.0f}")
        print(f"    Match score: {result['match_score']:.0f}")
    
    # Выбор лучшего
    best = max(results, key=lambda x: x["match_score"])
    print("\n" + "=" * 80)
    print(f"ЛУЧШИЙ СЦЕНАРИЙ: {best['name']}")
    print("=" * 80)
    print(f"  Total deals: {best['T']:,} (reference: {REFERENCE['T']:,})")
    print(f"  Paid deals:  {best['B']:,} (reference: {REFERENCE['B']:,})")
    print(f"  Difference:  T={best['t_diff']:+,}, B={best['b_diff']:+,}")
    
    # Продуктовый breakdown
    print("\n  Product breakdown:")
    print(f"  {'Product':<20} {'Deals':<12} {'Ref':<12} {'Diff':<10}")
    print(f"  {'-'*60}")
    for prod in ["Digital Marketing", "UX/UI Design", "Web Developer"]:
        if prod in best["products"]:
            calc = best["products"][prod]["T"]
            ref = REFERENCE["products"][prod]["T"]
            diff = calc - ref
            print(f"  {prod:<20} {calc:<12,} {ref:<12,} {diff:+10,}")
    
    # Применение фильтра
    print("\n[3] Применение выбранного фильтра...")
    filter_func = scenarios[best["name"]]
    
    deals_filtered = filter_func(deals.copy())
    print(f"  Deals: {len(deals):,} → {len(deals_filtered):,} ({len(deals_filtered)/len(deals)*100:.1f}%)")
    
    # Сохранение
    print("\n[4] Сохранение filtered datasets...")
    deals_filtered.to_parquet(CLEAN_DIR / "deals_filtered.parquet", index=False)
    deals_filtered.to_csv(CLEAN_DIR / "deals_filtered.csv", index=False, encoding="utf-8")
    
    # Metadata
    meta = {
        "filter_scenario": best["name"],
        "filter_description": "Удалены deals с пустым product (product=NA или отсутствует)",
        "rows_original": len(deals),
        "rows_filtered": len(deals_filtered),
        "rows_removed": len(deals) - len(deals_filtered),
        "removal_rate": (len(deals) - len(deals_filtered)) / len(deals),
        "paid_deals_original": int(deals["is_paid"].fillna(False).sum()),
        "paid_deals_filtered": best["B"],
        "match_to_reference": {
            "total_deals_diff": best["t_diff"],
            "paid_deals_diff": best["b_diff"],
            "match_score": best["match_score"],
        },
    }
    
    with open(CLEAN_DIR / "metadata_filtered.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ deals_filtered.parquet ({len(deals_filtered):,} rows)")
    print(f"  ✅ deals_filtered.csv")
    print(f"  ✅ metadata_filtered.json")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"📊 Filtered dataset: {len(deals_filtered):,} deals ({len(deals_filtered)/len(deals)*100:.1f}% от original)")
    print(f"📊 Removed: {len(deals) - len(deals_filtered):,} deals (в основном product=NA)")
    print(f"📊 Paid deals: {best['B']:,} (reference: {REFERENCE['B']:,})")
    
    if best["t_diff"] < 1000:
        print(f"✅ Match quality: ХОРОШИЙ (diff T={best['t_diff']:,}, B={best['b_diff']:,})")
    else:
        print(f"⚠️  Match quality: СРЕДНИЙ (diff T={best['t_diff']:,}, B={best['b_diff']:,})")
        print(f"   Возможно reference использует другое временное окно")
    
    print("\n💡 Следующий шаг: python scripts/10_compare_versions.py")


if __name__ == "__main__":
    main()
