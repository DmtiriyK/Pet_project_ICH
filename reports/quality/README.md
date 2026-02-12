# Data quality & descriptives (auto-generated)

Генерируется скриптом `scripts/03_descriptives_quality.py` из `data/clean/*.parquet`.

## Что внутри

Таблицы в `reports/quality/tables/`:
- `*_missingness.csv` — пропуски по всем колонкам
- `deals_numeric_summary.csv`, `spend_numeric_summary.csv`, `calls_numeric_summary.csv` — базовые метрики числовых полей (с модой)
- `deals_top_*.csv`, `calls_top_*.csv`, `spend_top_*.csv` — топ значений по ключевым категориальным полям

Графики в `reports/quality/figures/`:
- Гистограммы с KDE для revenue_cash, revenue_contract, sla_minutes
- Boxplots для ключевых числовых метрик
- Горизонтальные barplots для категориальных переменных (Stage, Source, Product, Quality, Payment Type, City, Level of Deutsch)
- Heatmap пропусков по всем таблицам

JSON:
- `reports/quality/shapes.json` — размеры таблиц
- `reports/quality/notes.json` — важные оговорки по данным

## Выводы

1. **Качество данных высокое**: Большинство критических полей (Stage, Source, Product, Payment Type) имеют минимальный процент пропусков (<5%). Основные пропуски сосредоточены в необязательных полях (Campaign, City, Education Type).

2. **Revenue имеет правый хвост**: Распределения revenue_cash и revenue_contract показывают сильную правостороннюю асимметрию (long tail). Большинство сделок - малые чеки, но есть выбросы с крупными контрактами, что типично для B2C образования.

3. **SLA minutes показывает бимодальность**: Распределение SLA (время от создания контакта до первого касания) имеет два пика - быстрые обработки (0-60 минут) и отложенные (>1 день). Требуется анализ влияния SLA на конверсию.

4. **Категориальные переменные сбалансированы**: Топ-5 источников (Google Ads, Facebook Ads, Bloggers, TikTok Ads, YouTube Ads) покрывают >80% сделок. Распределение по продуктам показывает доминирование 2-3 основных программ.

5. **Quality field субъективен**: Как указано в task.md, поле Quality является субъективной оценкой менеджера и не должно использоваться как прямой предиктор конверсии без дополнительной валидации.
