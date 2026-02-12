import pandas as pd
import numpy as np

print("="*70)
print("ГЛУБОКАЯ ПРОВЕРКА ИСХОДНОГО ФАЙЛА")
print("="*70)

# Load raw
raw = pd.read_excel('Deals (Done).xlsx')
print(f"\nИСХОДНЫЙ ФАЙЛ: {len(raw):,} rows")

# Check product field
raw['product_clean'] = raw['Product'].fillna('').str.strip()

# Count by product in RAW
print("\n" + "="*70)
print("ПРОДУКТЫ В ИСХОДНОМ ФАЙЛЕ (включая пустые)")
print("="*70)
prod_raw = raw['product_clean'].replace('', 'EMPTY').value_counts()
print(prod_raw)

# Filter to known products
raw_known = raw[
    (raw['product_clean'].notna()) & 
    (raw['product_clean'] != '') &
    (raw['product_clean'] != 'NA')
].copy()

print(f"\n" + "="*70)
print(f"RAW с известными продуктами: {len(raw_known):,} rows")
print("="*70)

# Count main products
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    count = (raw['product_clean'] == prod).sum()
    ref_count = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}[prod]
    diff = count - ref_count
    print(f"{prod:20s}: {count:,} (ref: {ref_count:,}, diff: {diff:+,})")

print("\n" + "="*70)
print("ПРОВЕРКА: может reference учитывает даты по-другому?")
print("="*70)

# Check date fields
raw['created'] = pd.to_datetime(raw['Created Time'], errors='coerce')
raw['closing'] = pd.to_datetime(raw['Closing Date'], errors='coerce')

# Our window
our_start = pd.Timestamp('2023-07-04')
our_end = pd.Timestamp('2024-06-21')

# Check different time windows
print(f"\nНаше окно: {our_start.date()} — {our_end.date()}")

# By created date (our approach)
by_created = raw[
    (raw['created'] >= our_start) & 
    (raw['created'] <= our_end) &
    (raw['product_clean'].isin(['Digital Marketing', 'UX/UI Design', 'Web Developer']))
]
print(f"\n1. По Created Time (наш подход): {len(by_created):,} deals")
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    count = (by_created['product_clean'] == prod).sum()
    ref_count = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}[prod]
    print(f"   {prod}: {count:,} vs ref {ref_count:,} ({count-ref_count:+,})")

# By closing date
by_closing = raw[
    (raw['closing'] >= our_start) & 
    (raw['closing'] <= our_end) &
    (raw['product_clean'].isin(['Digital Marketing', 'UX/UI Design', 'Web Developer']))
]
print(f"\n2. По Closing Date: {len(by_closing):,} deals")
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    count = (by_closing['product_clean'] == prod).sum()
    ref_count = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}[prod]
    print(f"   {prod}: {count:,} vs ref {ref_count:,} ({count-ref_count:+,})")

# Created OR Closing in period
by_either = raw[
    (((raw['created'] >= our_start) & (raw['created'] <= our_end)) |
     ((raw['closing'] >= our_start) & (raw['closing'] <= our_end))) &
    (raw['product_clean'].isin(['Digital Marketing', 'UX/UI Design', 'Web Developer']))
]
print(f"\n3. Created OR Closing в периоде: {len(by_either):,} deals")
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    count = (by_either['product_clean'] == prod).sum()
    ref_count = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}[prod]
    print(f"   {prod}: {count:,} vs ref {ref_count:,} ({count-ref_count:+,})")

# No time filter at all
no_time = raw[
    (raw['product_clean'].isin(['Digital Marketing', 'UX/UI Design', 'Web Developer']))
]
print(f"\n4. БЕЗ фильтрации по датам: {len(no_time):,} deals")
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    count = (no_time['product_clean'] == prod).sum()
    ref_count = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}[prod]
    print(f"   {prod}: {count:,} vs ref {ref_count:,} ({count-ref_count:+,})")

print("\n" + "="*70)
print("ВРЕМЯ: ДИАПАЗОНЫ ДАННЫХ")
print("="*70)
print(f"\nCreated Time:")
print(f"  Min: {raw['created'].min()}")
print(f"  Max: {raw['created'].max()}")
print(f"\nClosing Date:")
print(f"  Min: {raw['closing'].min()}")
print(f"  Max: {raw['closing'].max()}")
