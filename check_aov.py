import pandas as pd

df = pd.read_parquet('data/clean/deals_filtered.parquet')

print("REFERENCE AOV по продуктам:")
print("DM: 2,262,490/469 =", f"{2262490/469:.0f}€")
print("UX: 951,645/226 =", f"{951645/226:.0f}€")
print("WD: 366,680/135 =", f"{366680/135:.0f}€")

print("\nНАШИ AOV (contract = offer_total_amount):")
for p in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    paid = df[(df['product']==p) & (df['is_paid']==True)]
    if len(paid) > 0:
        aov = paid['revenue_contract'].sum() / len(paid)
        print(f"{p}: {paid['revenue_contract'].sum():.0f}/{len(paid)} = {aov:.0f}€")

print("\nНАШИ AOV (cash = initial_amount_paid):")
for p in ['Digital Marketing', 'UX/UI Design', 'Web Developer']:
    paid = df[(df['product']==p) & (df['is_paid']==True)]
    if len(paid) > 0:
        aov = paid['initial_amount_paid'].sum() / len(paid)
        print(f"{p}: {paid['initial_amount_paid'].sum():.0f}/{len(paid)} = {aov:.0f}€")

print("\nСРАВНЕНИЕ:")
print("Reference AOV: 4,824€ / 4,210€ / 2,716€")
print("Наш contract AOV слишком высокий (8K-4K)")
print("Наш cash AOV слишком низкий (1K)")
print("\nВозможно reference использует другое поле или расчёт?")
