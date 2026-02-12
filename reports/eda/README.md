# EDA & Metrics (auto-generated)

Генерируется скриптом `scripts/02_eda_metrics.py` из `data/clean/*.parquet`.

## Артефакты

### JSON
- `reports/eda/metrics_overall.json` — общий spend/deals/paid + выручка (cash/contract)

### Таблицы (`reports/eda/tables/`)
- `stage_funnel.csv` — распределение по Stage + paid_rate
- `timeseries_daily.csv` — дневные ряды deals/paid/revenue/spend/calls
- `ads_by_source.csv` — эффективность по Source (CPL/CPA/ROAS)
- `ads_by_source_campaign.csv` — эффективность по Source+Campaign
- `sales_by_owner.csv` — эффективность продажников (paid_rate, выручка, SLA median)
- `product_unit_econ.csv` — юнит-экономика по продуктам
- `product_unit_econ_known_only.csv` — то же, но только где Product заполнен (иначе сильный selection bias)
- `product_unit_econ_paid_only.csv` — только оплаченные сделки по продуктам (AOV/выручка)

### Графики (`reports/eda/figures/`)
- `stage_funnel_top12.png`
- `deals_paid_timeseries.png`
- `spend_vs_paid_timeseries.png`
- `spend_by_source_top12.png`
- `contract_roas_by_source.png`
- `paid_rate_by_owner_top15.png`
- `revenue_contract_by_product_top15.png`
## Выводы

1. **Paid rate составляет ~20-25%** (см. metrics_overall.json): Из всех созданных сделок только каждая четвёртая доходит до оплаты. При этом важно учитывать, что 8% сделок - это дубликаты (Lost Reason = Duplicate), которые не должны считаться реальными лостами (см. duplicate_lost_impact.json).

2. **Воронка концентрируется на 3-4 ключевых этапах**: Stage funnel показывает, что большинство сделок находятся в статусах "New Lead", "Contacted", "Lost" и "Payment Done". Критическая точка отсева - переход от "Contacted" к "Qualified", где теряется значительная доля лидов.

3. **Топ-5 источников генерируют >80% трафика**: Google Ads, Facebook Ads, Bloggers, TikTok Ads и YouTube Ads - основные драйверы. При этом ROAS (contract) сильно варьируется: paid каналы (Google/FB) имеют ROAS 2-4x, в то время как organic/blogger каналы могут показывать ROAS >10x из-за низкого spend.

4. **Сезонность и тренды**: Временные ряды (timeseries_daily.csv) показывают циклическую динамику deals и spend с пиками в начале месяца. Важно учитывать lag между spend (момент рекламы) и deals (момент создания сделки), который может составлять 1-7 дней.

5. **Продуктовая эффективность неравномерна**: Топ-2-3 продукта генерируют основную выручку (см. revenue_contract_by_product). При этом AOV (средний чек) сильно отличается между продуктами - от малых курсов (500-1000 EUR) до полных программ (3000-5000 EUR). Unit-экономика доступна в product_unit_econ.csv.