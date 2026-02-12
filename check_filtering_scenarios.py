import pandas as pd

# Load original raw data
deals_raw = pd.read_excel('Deals (Done).xlsx')
print(f"RAW DATA: {len(deals_raw):,} rows")

# Load our clean
deals_clean = pd.read_parquet('data/clean/deals.parquet')
print(f"CLEAN (Full): {len(deals_clean):,} rows")

# Load filtered
deals_filt = pd.read_parquet('data/clean/deals_filtered.parquet')
print(f"FILTERED: {len(deals_filt):,} rows")

print("\n" + "="*60)
print("АНАЛИЗ ФИЛЬТРАЦИИ")
print("="*60)

# Check what we removed
print(f"\nRaw → Clean: -{len(deals_raw) - len(deals_clean):,} (duplicates)")
print(f"Clean → Filtered: -{len(deals_clean) - len(deals_filt):,} (product=NA)")

# Check product distribution
print("\n" + "="*60)
print("PRODUCT DISTRIBUTION (Clean)")
print("="*60)
prod_counts = deals_clean['product'].value_counts(dropna=False)
print(prod_counts)

print("\n" + "="*60)
print("ПРОВЕРКА: что если считать по-другому?")
print("="*60)

# Scenario 1: Only 3 main products
main_prods = deals_clean[deals_clean['product'].isin(['Digital Marketing', 'UX/UI Design', 'Web Developer'])]
print(f"\n1. Only 3 main products: {len(main_prods):,} (ref: 4,572, diff: {len(main_prods)-4572:+,})")

# Scenario 2: Known products (not NA) INCLUDING minor products
known = deals_clean[(deals_clean['product'].notna()) & (deals_clean['product'] != 'NA')]
print(f"2. All known products: {len(known):,} (ref: 4,572, diff: {len(known)-4572:+,})")

# Scenario 3: Maybe they DON'T filter duplicates?
clean_with_dups = pd.read_excel('Deals (Done).xlsx')
clean_with_dups['product'] = clean_with_dups['Product'].str.strip()
known_with_dups = clean_with_dups[
    (clean_with_dups['product'].notna()) & 
    (clean_with_dups['product'] != 'NA') &
    (~clean_with_dups['product'].isin(['', 'nan', 'None']))
]
print(f"3. Known products БЕЗ удаления дубликатов: {len(known_with_dups):,} (ref: 4,572, diff: {len(known_with_dups)-4572:+,})")

# Scenario 4: Maybe they include duplicate_lost?
known_incl_dup = deals_clean[
    (deals_clean['product'].notna()) & 
    (deals_clean['product'] != 'NA')
]
print(f"4. Known + включая duplicate_lost: {len(known_incl_dup):,} (ref: 4,572, diff: {len(known_incl_dup)-4572:+,})")

# Check how many duplicate_lost
dup_lost_count = deals_clean['is_duplicate_lost'].sum()
print(f"   (из них duplicate_lost: {dup_lost_count:,})")

print("\n" + "="*60)
print("ПО ПРОДУКТАМ С/БЕЗ DUPLICATE_LOST")
print("="*60)

ref_counts = {'Digital Marketing': 2897, 'UX/UI Design': 1170, 'Web Developer': 505}

for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    prod_all = deals_clean[deals_clean['product'] == prod]
    prod_no_dup = prod_all[~prod_all['is_duplicate_lost']]
    dup_count = len(prod_all) - len(prod_no_dup)
    
    print(f"\n{prod}:")
    print(f"  С duplicate_lost: {len(prod_all):,}")
    print(f"  Без duplicate_lost: {len(prod_no_dup):,}")
    print(f"  Removed: {dup_count:,}")
    print(f"  Reference: {ref_counts[prod]:,}")
