без заполнений данных



# Итоговый проект 2 — CRM аналитика онлайн-школы немецкого языка

## ⚠️ КРИТИЧНО: Ограничения данных и метрик

### CPA/ROAS по продуктам — НЕЛЬЗЯ посчитать корректно!

**Проблема**: В данных **нет привязки Spend → Product**. Один рекламный источник генерирует лиды для РАЗНЫХ продуктов одновременно.

**Что известно:**
- `Spend` агрегирован по `Source + Campaign`
- `Deals` известны по `Source + Campaign + Product`

**Что это означает:**
```
Source: Instagram, Campaign: "Spring2024", Spend: 10,000 €
├─ Web Developer: 50 leads → 10 paid
├─ Digital Marketing: 100 leads → 20 paid
└─ UX/UI Design: 30 leads → 5 paid

❓ Сколько из 10,000€ пришлось на каждый продукт? → ❌ НЕИЗВЕСТНО
```

**Метрики по продуктам:**
- ✅ **Можно**: Revenue, AOV, Paid Rate, Volume (количество paid deals)
- ❌ **Нельзя**: CPA, CPL, ROAS (нужна аллокация spend)

**См. подробности**: [DISCLAIMER_PRODUCT_METRICS.md](reports/DISCLAIMER_PRODUCT_METRICS.md)

---

## О проекте

Анализ эффективности маркетинга и продаж для онлайн-школы немецкого языка на основе данных CRM (сделки, контакты, звонки) и рекламных расходов.

**Цели**:
- Оценить эффективность рекламных каналов (CPL, CPA, ROAS)
- Построить воронку продаж и выявить узкие места
- Проанализировать связь звонков и конверсии
- Провести продуктовую и географическую сегментацию
- Создать интерактивный дашборд и презентацию для стейкхолдеров

**Данные**: 4 таблицы (Contacts, Calls, Deals, Spend) за период 2023-2024, ~21K сделок, ~96K звонков, ~19K контактов.

---

## Структура проекта

```
.
├── data/
│   └── clean/              # Очищенные данные (Parquet + CSV)
├── notebooks/              # Jupyter notebooks для исследования
│   └── 02_eda_metrics.ipynb
├── scripts/                # Pipeline скрипты (01-09)
│   ├── 01_clean_export.py  # Очистка и создание флагов (is_paid, is_duplicate_lost)
│   ├── 02_eda_metrics.py   # Общие метрики, воронка, временные ряды
│   ├── 02b_duplicate_lost_analysis.py  # Анализ дубликатов (КРИТИЧНО)
│   ├── 03_descriptives_quality.py      # Описательная статистика + визуализации
│   ├── 04_time_analysis.py             # Time-to-close, сезонность
│   ├── 04b_calls_deals_link.py         # Связь звонков-сделок (КРИТИЧНО)
│   ├── 05_metrics_tree.py              # Дерево метрик с Sankey диаграммами
│   ├── 06_segmentation.py              # Продуктовая и гео-сегментация
│   ├── 07_build_report.py              # Генерация markdown отчёта
│   ├── 08_make_presentation.py         # Генерация PPTX/HTML слайдов
│   └── 09_export_pdf.py                # Экспорт в PDF (опционально)
├── reports/                # Все результаты анализа
│   ├── quality/            # Описательная статистика (tables + figures)
│   ├── eda/                # EDA метрики, воронка, временные ряды
│   ├── time/               # Временной анализ (time-to-close, seasonality)
│   ├── metrics_tree/       # Дерево метрик (Sankey + block schema)
│   ├── calls_deals/        # Анализ связи звонков-сделок
│   ├── segments/           # Продуктовая и гео-сегментация
│   ├── insights/           # Инсайты (опционально)
│   └── final/              # Итоговый отчёт + презентация
├── app.py                  # Streamlit дашборд
├── requirements.txt        # Python зависимости
├── task.md                 # Требования к проекту (source of truth)
└── README.md               # Этот файл
```

---

## Быстрый старт

### 1. Установить зависимости

```powershell
python -m pip install -r requirements.txt
```

### 2. Запустить полный pipeline

```powershell
# Шаг 1: Очистка данных (обязательно)
python scripts/01_clean_export.py

# Шаг 2: Основные метрики и EDA
python scripts/02_eda_metrics.py

# Шаг 2b: Анализ дубликатов (критично!)
python scripts/02b_duplicate_lost_analysis.py

# Шаг 3: Описательная статистика с визуализациями
python scripts/03_descriptives_quality.py

# Шаг 4: Временной анализ
python scripts/04_time_analysis.py

# Шаг 4b: Связь звонков-сделок (критично!)
python scripts/04b_calls_deals_link.py

# Шаг 5: Дерево метрик с Sankey
python scripts/05_metrics_tree.py

# Шаг 6: Сегментация
python scripts/06_segmentation.py

# Шаг 7: Генерация отчёта
python scripts/07_build_report.py

# Шаг 8: Презентация
python scripts/08_make_presentation.py
```

### 3. Запустить дашборд

```powershell
streamlit run app.py
```

Откроется интерактивный дашборд с 8+ вкладками:
- Overview (KPIs)
- Ads Performance
- Sales Funnel
- Products
- Payments
- Geography
- Time Analysis
- Notes & Methodology

---

## Ключевые артефакты

### Метрики и аналитика

- **Общие метрики**: `reports/eda/metrics_overall.json` — Spend, Deals, Paid Rate, Revenue
- **Дерево метрик**: `reports/metrics_tree/metrics_tree_overall_overlap_window.json` — CPL, CPA, ROAS breakdown
- **Дубликаты**: `reports/eda/duplicate_lost_impact.json` — Влияние дубликатов на метрики (8% сделок, +0.35 pp на paid rate)
- **Звонки-сделки**: `reports/calls_deals/coverage_stats.json` — 95.78% сделок с звонками, avg 17.5 calls/deal

### Визуализации

- **Sankey дерево метрик**: `reports/metrics_tree/figures/sankey_overall.png`
- **Воронка по Stage**: `reports/eda/figures/stage_funnel_top12.png`
- **Временные ряды**: `reports/eda/figures/deals_paid_timeseries.png`
- **Звонки vs Paid Rate**: `reports/calls_deals/figures/calls_vs_paid_rate.png`
- **13+ дополнительных графиков** в `reports/quality/figures/` и `reports/eda/figures/`

### Отчёты

- **Финальный отчёт**: `reports/final/report.md`
- **Презентация**: `reports/final/slides.html` (открывается в браузере)
- **Outline презентации**: `reports/final/presentation_outline.md`

---

## Важное про ID контактов

В исходных `Calls.CONTACTID` и `Deals.Contact Name` ID сохранены как числа в Excel, поэтому при чтении теряются последние цифры (ограничение float).

Скрипт сохраняет:
- `contact_id_str` — восстановление через округление (может быть неточным)
- `contact_id15` — первые 15 цифр для "мягких" связок (не уникально, возможны коллизии)

Для точных джойнов лучше опираться на `Deals` + `Spend` по `source/campaign` и времени, а Calls использовать агрегированно.

---

## Критические правила (из task.md)

1. **Paid definition**: `Stage == "Payment Done"` (case-insensitive) → `is_paid = True`
2. **Duplicate Lost**: `Lost Reason == "Duplicate"` → это НЕ реальный лост, а дубль контакта. Флаг `is_duplicate_lost` создаётся автоматически и **должен исключаться** из анализа потерь.
3. **Quality field**: Субъективная оценка менеджера, не использовать как прямой предиктор конверсии.
4. **Revenue**: 
   - `revenue_cash` — фактически полученные деньги
   - `revenue_contract` — полная стоимость контракта (используется для ROAS)

---

## Known Limitations

1. **Contact ID corruption**: Excel float ограничения делают точные Contacts→Calls→Deals джойны ненадёжными. Используем агрегированный анализ по источникам/времени.

2. **Time lag между Spend и Deals**: Рекламные расходы (Spend) конвертируются в сделки (Deals) с задержкой 3-7 дней. При расчёте ROAS нужна корректировка окон.

3. **Missingness в Campaign/City**: ~20-30% пропусков в необязательных полях. Анализ проводится с фильтрацией по `min_deals` для статистической значимости.

4. **Quality field субъективность**: Оценка качества лида ("A", "B", "C") — личное мнение менеджера, не использовать для predictive моделей без валидации.

---

## Технологии

- **Python 3.11+**
- **Data**: pandas, numpy, pyarrow (Parquet)
- **Visualization**: plotly, matplotlib, seaborn, kaleido
- **Dashboard**: streamlit
- **Presentation**: python-pptx, markdown, playwright (PDF export)
- **Notebooks**: jupyter

---

## Автор

Проект выполнен в рамках итоговой работы по курсу аналитики данных.

---

## Changelog

- **v1.3** (2024-01): ✅ Добавлены критические блоки: Sankey визуализации, графики описательной статистики, мода в метриках, анализ связи звонков-сделок, анализ дубликатов, выводы во всех README
- **v1.2** (2024-01): Дашборд + презентация
- **v1.1** (2024-01): Pipeline скриптов 01-08
- **v1.0** (2024-01): Начальная версия с очисткой данных
