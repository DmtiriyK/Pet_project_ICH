from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_money(x: float) -> str:
    return f"{x:,.2f}"


def _fmt_int(x: float | int) -> str:
    return f"{int(x):,}"


def main() -> None:
    out_dir = ROOT / "reports" / "final"
    out_dir.mkdir(parents=True, exist_ok=True)

    overall = _read_json(ROOT / "reports" / "eda" / "metrics_overall.json")
    ttc = _read_json(ROOT / "reports" / "time" / "paid_time_to_close_stats.json")

    ads = pd.read_csv(ROOT / "reports" / "eda" / "tables" / "ads_by_source.csv")
    sales = pd.read_csv(ROOT / "reports" / "eda" / "tables" / "sales_by_owner.csv")
    products_paid = pd.read_csv(ROOT / "reports" / "eda" / "tables" / "product_unit_econ_paid_only.csv")
    paid_by_payment = pd.read_csv(ROOT / "reports" / "segments" / "tables" / "paid_by_payment_type.csv")
    paid_by_edu = pd.read_csv(ROOT / "reports" / "segments" / "tables" / "paid_by_education_type.csv")
    funnel_city = pd.read_csv(ROOT / "reports" / "segments" / "tables" / "funnel_by_city_min80.csv")
    funnel_de = pd.read_csv(ROOT / "reports" / "segments" / "tables" / "funnel_by_level_of_deutsch_min80.csv")

    top_ads = ads.sort_values("spend", ascending=False).head(8)
    top_sales = sales.sort_values("paid_rate", ascending=False).head(8)
    top_products = products_paid.sort_values("revenue_contract", ascending=False).head(8)
    top_payment = paid_by_payment.sort_values("revenue_contract", ascending=False).head(8)
    top_edu = paid_by_edu.sort_values("revenue_contract", ascending=False).head(8)
    top_city = funnel_city.sort_values("paid_rate", ascending=False).head(8)
    top_de = funnel_de.sort_values("paid_rate", ascending=False).head(8)

    def df_to_md(df: pd.DataFrame) -> str:
        try:
            return df.to_markdown(index=False)
        except Exception:
            header = "| " + " | ".join(df.columns) + " |"
            sep = "| " + " | ".join(["---"] * len(df.columns)) + " |"
            rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
            return "\n".join([header, sep, *rows])

    report_md = f"""# CRM аналитика — отчёт (черновик)

Дата генерации: авто

## 1) Данные

Таблицы:
- `Contacts` — контакты лидов
- `Calls` — звонки по контактам
- `Deals` — сделки (главная таблица)
- `Spend` — рекламные расходы

Ключевые правила из методички:
- Оплаченная сделка: **только** `Stage = Payment Done`
- `Closing Date` — дата оплаты (но в данных у paid может быть пустым)
- `Lost Reason = Duplicate` — не реальный лост (дубликаты)

Оговорка по ID: в `Calls.CONTACTID` и `Deals.Contact Name` ID пришли как Excel-числа → точный джойн Contacts↔Calls↔Deals не гарантируется.

## 2) Очистка

Скрипт: `scripts/01_clean_export.py`

Что сделано:
- нормализация имён колонок и строковых значений
- приведение типов (даты/суммы/длительности)
- удаление точных дублей (Spend/Deals)
- добавление флагов/метрик: `is_paid`, `is_duplicate_lost`, `revenue_cash`, `revenue_contract`, `sla_minutes`

## 3) Общая картинка (окно пересечения Spend и Deals)

- Spend total: **{_fmt_money(overall['spend_total'])}**
- Deals total: **{_fmt_int(overall['deals_total'])}**
- Paid deals: **{_fmt_int(overall['paid_deals'])}** (paid rate ≈ **{overall['paid_rate']:.2%}**)
- Revenue (cash): **{_fmt_money(overall['revenue_cash_total'])}**
- Revenue (contract): **{_fmt_money(overall['revenue_contract_total'])}**

## 4) Временной анализ

Time-to-close по paid сделкам считаем только там, где есть обе даты:
- Paid deals: **{_fmt_int(ttc['paid_deals'])}**
- Paid with closing date: **{_fmt_int(ttc['paid_with_closing_date'])}** (coverage **{ttc['coverage_pct']:.2f}%**)
- Median lag (days): **{ttc['lag_days_median']:.2f}**
- P90 lag (days): **{ttc['lag_days_p90']:.2f}**

Артефакты: `reports/time/`.

## 5) Эффективность продажников (главный инсайт №1)

Топ по paid_rate:

{df_to_md(top_sales[['deal_owner_name','deals','paid_deals','paid_rate','revenue_contract','sla_minutes_median']])}

Интерпретация:
- сильный разброс paid_rate между менеджерами → конверсия зависит от процесса/исполнителя
- это хороший кандидат на 2-недельный пилот: скрипт/контроль SLA/квалификация/распределение лидов

Артефакты: `reports/eda/tables/sales_by_owner.csv`.

## 6) Эффективность рекламы (Source)

Топ источников по spend (с CPL/CPA/ROAS):

{df_to_md(top_ads[['source','spend','leads','paid_deals','cpa','contract_roas']].rename(columns={'leads':'deals'}))}

Артефакты: `reports/eda/tables/ads_by_source.csv`.

## 7) Продукты (paid-only)

{df_to_md(top_products[['product','paid_deals','revenue_contract','contract_aov_paid']])}

Артефакты: `reports/eda/tables/product_unit_econ_paid_only.csv`.

## 8) Гипотезы роста (2 недели)

1) **Продажи (главная)** — репликация практик топ-менеджеров: пилот по скрипту/контролю SLA/квалификации на части менеджеров.
   - Метрики: `paid_rate`, `revenue_contract` по `deal_owner_name`.
   - Дизайн: пилотная группа A vs контроль B, одинаковые источники лидов.
   - Критерий: рост paid_rate в A при сохранении объёма обработанных сделок.

2) **Реклама** — перераспределение бюджета: снизить spend в кампаний/источниках с высоким `CPA` и низким `ROAS`, перераспределить в более эффективные.
   - Метрики: `contract_roas`, `cpa` по Source/Campaign, объём `paid_deals`.
   - Критерий: рост ROAS при сохранении/росте paid_deals.

Подробный черновик: `reports/insights/README.md`.

## 9) Платежи / образование / гео (сегменты)

### Payment Type (paid-only)
{df_to_md(top_payment[['payment_type','paid_deals','revenue_contract','contract_aov_paid']])}

### Education Type (paid-only)
{df_to_md(top_edu[['education_type','paid_deals','revenue_contract','contract_aov_paid']])}

### City (min 80 deals)
{df_to_md(top_city[['city','deals','paid_deals','paid_rate','revenue_contract']])}

### Level of Deutsch (min 80 deals)
{df_to_md(top_de[['level_of_deutsch','deals','paid_deals','paid_rate','revenue_contract']])}
"""

    (out_dir / "report.md").write_text(report_md, encoding="utf-8-sig")

    pres_md = f"""# Презентация — структура (черновик)

1. Контекст и цель
2. Что за данные (4 таблицы) + оговорки по ID
3. Как чистили (коротко) + что считаем оплатой
4. Метрики сверху (Spend / Deals / Paid / Revenue cash+contract)
5. Воронка по Stage (скрин из `reports/eda/figures/stage_funnel_top12.png`)
6. Продажи (главный инсайт): разброс по менеджерам + что это значит
7. Реклама: топ источников + где слив (CPA/ROAS)
8. Продукты: выручка и AOV по paid-only
9. Платежи/обучение/гео: сегменты (коротко)
10. Время: time-to-close (coverage, медиана, p90) + где теряем время
11. 2 гипотезы роста + как тестить за 2 недели
12. Риски/ограничения данных + что улучшить в сборе

Ключевые числа:
- Spend: {_fmt_money(overall['spend_total'])}
- Paid deals: {_fmt_int(overall['paid_deals'])} (rate {overall['paid_rate']:.2%})
- Revenue contract: {_fmt_money(overall['revenue_contract_total'])}
"""
    (out_dir / "presentation_outline.md").write_text(pres_md, encoding="utf-8-sig")

    print("OK: reports/final ready")


if __name__ == "__main__":
    main()
