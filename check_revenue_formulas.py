import pandas as pd

df = pd.read_parquet('data/clean/deals_filtered.parquet')
paid = df[df['is_paid'] == True].copy()

print("ТЕСТИРОВАНИЕ REVENUE FORMULAS:")
print("="*70)
print(f"\nReference revenue: 3,580,815€")
print(f"Наш contract total: {paid['revenue_contract'].sum():,.0f}€")
print(f"Наш cash total: {paid['initial_amount_paid'].sum():,.0f}€")

print("\n" + "="*70)
print("ПРОВЕРКА РАЗНЫХ ФОРМУЛ:")
print("="*70)

# Formula 1: Contract / 2
rev1 = paid['revenue_contract'].sum() / 2
match1 = rev1 / 3580815
print(f"\n1. Contract / 2 = {rev1:,.0f}€ (match: {match1:.2%})")

# Formula 2: Cash * multiplier
for mult in [2, 3, 3.5, 4, 4.5, 5]:
    rev = paid['initial_amount_paid'].sum() * mult
    match = rev / 3580815
    print(f"2. Cash * {mult} = {rev:,.0f}€ (match: {match:.2%})")

# Formula 3: Weighted average
print(f"\n3. Weighted averages:")
for w_cash in [0.2, 0.3, 0.4, 0.5, 0.6]:
    w_contract = 1 - w_cash
    rev = (paid['initial_amount_paid'].sum() * w_cash + 
           paid['revenue_contract'].sum() * w_contract)
    match = rev / 3580815
    print(f"   Cash*{w_cash:.1f} + Contract*{w_contract:.1f} = {rev:,.0f}€ (match: {match:.2%})")

# Formula 4: Offer_total_amount (если отличается от revenue_contract)
if 'offer_total_amount' in paid.columns:
    rev4 = paid[paid['offer_total_amount'].notna()]['offer_total_amount'].sum()
    match4 = rev4 / 3580815
    print(f"\n4. Offer_total_amount direct = {rev4:,.0f}€ (match: {match4:.2%})")

# Formula 5: По продуктам (может разные multipliers?)
print(f"\n5. Проверка по продуктам (cash * X):")
total_calc = 0
for prod in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    prod_paid = paid[paid['product'] == prod]
    cash = prod_paid['initial_amount_paid'].sum()
    contract = prod_paid['revenue_contract'].sum()
    
    # Reference values
    ref_revs = {
        'Digital Marketing': 2262490,
        'UX/UI Design': 951645,
        'Web Developer': 366680
    }
    ref_rev = ref_revs[prod]
    
    if cash > 0:
        multiplier = ref_rev / cash
        print(f"   {prod}: cash {cash:,.0f} * {multiplier:.2f} = {ref_rev:,.0f}")
        total_calc += ref_rev

print(f"\n   Total если использовать product-specific multipliers: {total_calc:,.0f}")
print(f"   Reference total: 3,580,815")
print(f"   Match: {total_calc/3580815:.2%}")
