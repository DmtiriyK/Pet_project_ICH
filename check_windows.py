import pandas as pd
from datetime import datetime

df = pd.read_parquet('data/clean/deals_filtered.parquet')
spend = pd.read_parquet('data/clean/spend.parquet')

print("ТЕКУЩИЕ ВРЕМЕННЫЕ ГРАНИЦЫ:")
print("="*60)

# Deals
df['created_date'] = pd.to_datetime(df['created_time']).dt.date
print(f"\nDeals (filtered, {len(df):,} rows):")
print(f"  Min date: {df['created_date'].min()}")
print(f"  Max date: {df['created_date'].max()}")

# По продуктам
print(f"\nПо продуктам:")
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    prod_df = df[df['product'] == prod]
    print(f"  {prod}:")
    print(f"    {len(prod_df):,} deals, {prod_df['created_date'].min()} to {prod_df['created_date'].max()}")

# Spend
spend['date'] = pd.to_datetime(spend['date']).dt.date
print(f"\nSpend ({len(spend):,} rows):")
print(f"  Min date: {spend['date'].min()}")
print(f"  Max date: {spend['date'].max()}")

# Overlap
overlap_start = max(df['created_date'].min(), spend['date'].min())
overlap_end = min(df['created_date'].max(), spend['date'].max())
print(f"\nOverlap window: {overlap_start} to {overlap_end}")

# Проверка разных окон
print("\n" + "="*60)
print("ТЕСТИРОВАНИЕ РАЗНЫХ ОКОН:")
print("="*60)

windows = [
    ("Full window", df['created_date'].min(), df['created_date'].max()),
    ("2023 only", pd.Timestamp('2023-01-01').date(), pd.Timestamp('2023-12-31').date()),
    ("2024 only", pd.Timestamp('2024-01-01').date(), pd.Timestamp('2024-12-31').date()),
    ("H2 2023", pd.Timestamp('2023-07-01').date(), pd.Timestamp('2023-12-31').date()),
    ("H1 2024", pd.Timestamp('2024-01-01').date(), pd.Timestamp('2024-06-30').date()),
]

for name, start, end in windows:
    window_df = df[(df['created_date'] >= start) & (df['created_date'] <= end)]
    paid = window_df['is_paid'].fillna(False).sum()
    print(f"\n{name} ({start} to {end}):")
    print(f"  Deals: {len(window_df):,} (ref: 4,572, diff: {len(window_df)-4572:+,})")
    print(f"  Paid:  {paid:,} (ref: 843, diff: {paid-843:+,})")
    if paid > 0:
        revenue = window_df[window_df['is_paid']==True]['revenue_contract'].sum()
        print(f"  Revenue: {revenue:,.0f} (ref: 3,580,815, ratio: {revenue/3580815:.2f}x)")
