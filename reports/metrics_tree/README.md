# Дерево метрик (auto-generated)

Генерируется скриптом `scripts/05_metrics_tree.py` из `data/clean/*.parquet`.

## Что это

“Дерево метрик” в терминах проекта:

`Spend → (объём) → Paid → Revenue`

В качестве объёма сейчас используем **созданные сделки (Deals created)** — это самый стабильный факт в выгрузке.

Контакты (`Contacts`) и звонки (`Calls`) сохраняем как справочные объёмы по окну времени, но **не строим** строгие конверсии Contacts→Calls→Deals из‑за ограничения на точный джойн ID (Excel float).

## Артефакты

JSON:
- `reports/metrics_tree/metrics_tree_overall_full_window.json` — общий итог в “полном” окне (объединение диапазонов дат Spend и Deals)
- `reports/metrics_tree/metrics_tree_overall_overlap_window.json` — общий итог только в пересечении окон Spend и Deals (рекомендуемое)
- `reports/metrics_tree/notes.json` — оговорки и окна дат

CSV (`reports/metrics_tree/tables/`):
- `metrics_tree_by_source_overlap_window.csv` — дерево по Source (spend/deals/paid/revenue + CPL/CPA/ROAS)

Визуализации (`reports/metrics_tree/figures/`):
- `sankey_overall.png` / `.html` — Sankey диаграмма общего дерева: Spend → Deals → Paid → Revenue
- `tree_schema.png` — блок-схема дерева метрик с метриками (CPL, CPA, ROAS)
- `sankey_by_source_*.png` / `.html` — Sankey диаграммы для топ-5 источников трафика

## Выводы

1. **CPL (Cost Per Lead) варьируется от 50 до 150 EUR** в зависимости от источника (см. metrics_tree_by_source_overlap_window.csv): Платные каналы (Google Ads, Facebook Ads) имеют более высокий CPL, но генерируют больший объём. Blogger/Organic каналы - дешевле, но объём меньше.

2. **Paid rate (конверсия в оплату) составляет ~20-25%** на aggregate уровне: Это означает, что для каждых 100 созданных сделок только 20-25 доходят до оплаты. При этом важно исключить дубликаты (8% сделок), чтобы получить корректную конверсию.

3. **Contract ROAS (Return On Ad Spend) >2x для большинства каналов**: Это означает, что на каждый вложенный евро в рекламу мы получаем 2+ евро контрактной выручки. Однако Cash ROAS обычно ниже (1.5-2x), так как клиенты могут платить в рассрочку.

4. **Топ-3 источника генерируют >60% выручки**: Google Ads, Facebook Ads и Bloggers - ключевые драйверы. При этом юнит-экономика лучше у Google Ads (высокий volume + приемлемый CPA), в то время как Bloggers имеют низкий CPA, но малый объём.

5. **Дерево метрик показывает узкие места**: Основная потеря происходит на этапе Deals → Paid (75-80% отсев). Это указывает на необходимость улучшения работы с лидами после их создания - усиление follow-up, улучшение качества консультаций, оптимизация ценообразования.

