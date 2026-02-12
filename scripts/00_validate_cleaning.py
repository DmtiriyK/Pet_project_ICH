"""
Validation Script: Проверка корректности очистки данных

Этот скрипт валидирует, что все критические правила из методички соблюдены.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"


def validate_deals() -> dict:
    """Валидация таблицы Deals"""
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    
    results = {}
    
    # 1. Проверка is_paid флага
    payment_done_count = (deals["stage"].str.strip().str.lower() == "payment done").sum()
    is_paid_count = deals["is_paid"].sum()
    results["paid_flag_correct"] = (payment_done_count == is_paid_count)
    results["paid_deals_count"] = int(is_paid_count)
    
    # 2. Проверка revenue только для paid
    non_paid_with_revenue = deals[~deals["is_paid"] & (deals["revenue_contract"] > 0)]
    results["revenue_only_for_paid"] = len(non_paid_with_revenue) == 0
    results["invalid_revenue_records"] = len(non_paid_with_revenue)
    
    # 3. Проверка is_duplicate_lost флага
    lost_duplicate = deals[
        (deals["stage"].str.strip().str.lower() == "lost") & 
        (deals["lost_reason"].str.strip().str.lower() == "duplicate")
    ]
    results["duplicate_lost_count"] = len(lost_duplicate)
    results["duplicate_lost_flag_count"] = int(deals["is_duplicate_lost"].sum())
    results["duplicate_lost_correct"] = (len(lost_duplicate) == deals["is_duplicate_lost"].sum())
    
    # 4. Проверка типов данных
    results["created_time_is_datetime"] = pd.api.types.is_datetime64_any_dtype(deals["created_time"])
    results["closing_date_is_datetime"] = pd.api.types.is_datetime64_any_dtype(deals["closing_date"])
    results["sla_minutes_is_numeric"] = pd.api.types.is_numeric_dtype(deals["sla_minutes"])
    
    # 5. Проверка initial_amount_paid может быть пустым для paid
    paid_deals = deals[deals["is_paid"]]
    paid_without_initial = paid_deals["initial_amount_paid"].isna().sum()
    results["paid_without_initial_amount"] = int(paid_without_initial)
    results["paid_without_initial_pct"] = paid_without_initial / len(paid_deals) if len(paid_deals) > 0 else 0
    
    # 6. Проверка closing_date может быть пустым для paid
    paid_without_closing = paid_deals["closing_date"].isna().sum()
    results["paid_without_closing_date"] = int(paid_without_closing)
    results["paid_without_closing_pct"] = paid_without_closing / len(paid_deals) if len(paid_deals) > 0 else 0
    
    return results


def validate_spend() -> dict:
    """Валидация таблицы Spend"""
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")
    
    results = {}
    
    # 1. Проверка типов
    results["date_is_date"] = str(spend["date"].dtype) in ["object", "datetime64[ns]"]
    results["spend_is_numeric"] = pd.api.types.is_numeric_dtype(spend["spend"])
    results["impressions_is_integer"] = pd.api.types.is_integer_dtype(spend["impressions"])
    results["clicks_is_integer"] = pd.api.types.is_integer_dtype(spend["clicks"])
    
    # 2. Проверка дубликатов
    results["no_duplicates"] = spend.duplicated().sum() == 0
    
    # 3. Проверка отрицательных значений
    results["no_negative_spend"] = (spend["spend"] >= 0).all()
    results["no_negative_clicks"] = (spend["clicks"].fillna(0) >= 0).all()
    
    return results


def validate_contacts() -> dict:
    """Валидация таблицы Contacts"""
    contacts = pd.read_parquet(CLEAN_DIR / "contacts.parquet")
    
    results = {}
    
    # 1. Проверка типов
    results["created_time_is_datetime"] = pd.api.types.is_datetime64_any_dtype(contacts["created_time"])
    results["modified_time_is_datetime"] = pd.api.types.is_datetime64_any_dtype(contacts["modified_time"])
    
    # 2. Проверка contact_id обработан
    results["has_contact_id15"] = "contact_id15" in contacts.columns
    results["contact_id15_not_empty"] = contacts["contact_id15"].notna().sum() > 0
    
    return results


def validate_calls() -> dict:
    """Валидация таблицы Calls"""
    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    
    results = {}
    
    # 1. Проверка типов
    results["call_start_time_is_datetime"] = pd.api.types.is_datetime64_any_dtype(calls["call_start_time"])
    results["call_duration_seconds_is_integer"] = pd.api.types.is_integer_dtype(calls["call_duration_seconds"])
    results["call_duration_minutes_is_numeric"] = pd.api.types.is_numeric_dtype(calls["call_duration_minutes"])
    
    # 2. Проверка contact_id обработан
    results["has_contact_id15"] = "contact_id15" in calls.columns
    
    # 3. Проверка отрицательных длительностей
    results["no_negative_duration"] = (calls["call_duration_seconds"].fillna(0) >= 0).all()
    
    return results


def main():
    print("=" * 80)
    print("VALIDATION REPORT: Data Cleaning")
    print("=" * 80)
    print()
    
    print("📊 DEALS Validation")
    print("-" * 80)
    deals_results = validate_deals()
    for key, value in deals_results.items():
        status = "✅" if value in [True, 0] or (isinstance(value, (int, float)) and value >= 0) else "⚠️"
        print(f"{status} {key}: {value}")
    print()
    
    print("💰 SPEND Validation")
    print("-" * 80)
    spend_results = validate_spend()
    for key, value in spend_results.items():
        status = "✅" if value == True else "❌"
        print(f"{status} {key}: {value}")
    print()
    
    print("📇 CONTACTS Validation")
    print("-" * 80)
    contacts_results = validate_contacts()
    for key, value in contacts_results.items():
        status = "✅" if value == True else "❌"
        print(f"{status} {key}: {value}")
    print()
    
    print("📞 CALLS Validation")
    print("-" * 80)
    calls_results = validate_calls()
    for key, value in calls_results.items():
        status = "✅" if value == True else "❌"
        print(f"{status} {key}: {value}")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_checks = {
        "Deals": deals_results,
        "Spend": spend_results,
        "Contacts": contacts_results,
        "Calls": calls_results
    }
    
    critical_passed = True
    
    # Critical checks
    critical_checks = [
        ("Deals", "paid_flag_correct"),
        ("Deals", "revenue_only_for_paid"),
        ("Deals", "duplicate_lost_correct"),
        ("Spend", "no_duplicates"),
        ("Spend", "no_negative_spend"),
    ]
    
    print("\n🔴 CRITICAL CHECKS:")
    for table, check in critical_checks:
        value = all_checks[table][check]
        # Fix: proper boolean check
        is_pass = (value == True) if isinstance(value, bool) else value
        status = "✅ PASS" if is_pass else "❌ FAIL"
        print(f"  {status}: {table}.{check} = {value}")
        if not is_pass:
            critical_passed = False
    
    print()
    if critical_passed:
        print("🎉 ВСЕ КРИТИЧЕСКИЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("✅ Очистка данных выполнена корректно согласно методичке.")
    else:
        print("⚠️ ВНИМАНИЕ: Есть критические проблемы!")
        print("❌ Необходимо исправить очистку данных.")
    
    print()
    print("📋 ADDITIONAL NOTES:")
    print(f"  - Paid deals: {deals_results['paid_deals_count']}")
    print(f"  - Duplicate lost: {deals_results['duplicate_lost_count']} deals marked correctly")
    print(f"  - Paid without initial_amount: {deals_results['paid_without_initial_pct']:.1%} (OK per методичка)")
    print(f"  - Paid without closing_date: {deals_results['paid_without_closing_pct']:.1%} (known issue)")
    print()


if __name__ == "__main__":
    main()
