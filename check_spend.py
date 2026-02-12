import pandas as pd

spend = pd.read_parquet('data/clean/spend.parquet')
total_spend = spend['spend'].sum()
print(f"Total spend: {total_spend:,.2f} €")
