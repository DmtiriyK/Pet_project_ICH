"""
Добавление realistic revenue field к filtered dataset
Formula: Cash * 0.5 + Contract * 0.5 (weighted average)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "data" / "clean"

print("Добавление revenue_realistic к filtered dataset...")

# Load
df = pd.read_parquet(CLEAN_DIR / "deals_filtered.parquet")

# Add realistic revenue field
df['revenue_realistic'] = df['initial_amount_paid'] * 0.5 + df['offer_total_amount'] * 0.5

# Verification
print(f"\n✅ Created revenue_realistic field")
print(f"   Formula: initial_amount_paid * 0.5 + offer_total_amount * 0.5")

paid = df[df['is_paid'] == True]
total_realistic = paid['revenue_realistic'].sum()
total_contract = paid['revenue_contract'].sum()
total_cash = paid['revenue_cash'].sum()

print(f"\nRevenue comparison:")
print(f"   Contract: {total_contract:,.0f}€")
print(f"   Realistic: {total_realistic:,.0f}€ ← NEW")
print(f"   Cash: {total_cash:,.0f}€")
print(f"   Reference: 3,580,815€")
print(f"   Match: {total_realistic/3580815:.2%}")

# Save
df.to_parquet(CLEAN_DIR / "deals_filtered.parquet", index=False)
print(f"\n✅ Updated deals_filtered.parquet")
