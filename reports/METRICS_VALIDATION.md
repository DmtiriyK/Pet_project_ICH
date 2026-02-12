# ✅ Валидация метрик проекта — Что считаем корректно

## Обзор

После проверки данных и методологии расчётов, этот документ подтверждает **какие метрики рассчитаны корректно**, а **какие имеют ограничения** из-за структуры данных.

---

## ✅ Корректные метрики (валидированы)

### 1. Общие метрики (Overall)

**Scope**: Окно пересечения Spend и Deals

| Метрика | Формула | Источник | Статус |
|---------|---------|----------|--------|
| **Spend Total** | SUM(spend) | spend.csv | ✅ Корректно |
| **Deals Total** | COUNT(deals) | deals.csv | ✅ Корректно |
| **Paid Deals** | COUNT(deals WHERE stage='Payment Done') | deals.csv | ✅ Корректно |
| **Paid Rate** | Paid Deals / Deals Total | calculated | ✅ Корректно |
| **Revenue (cash)** | SUM(initial_amount_paid) from paid deals | deals.csv | ✅ Корректно |
| **Revenue (contract)** | SUM(offer_total_amount) from paid deals | deals.csv | ✅ Корректно |
| **CPL** | Spend Total / Deals Total | calculated | ✅ Корректно (на уровне overall) |
| **CPA** | Spend Total / Paid Deals | calculated | ✅ Корректно (на уровне overall) |
| **ROAS (cash)** | Revenue (cash) / Spend Total | calculated | ✅ Корректно |
| **ROAS (contract)** | Revenue (contract) / Spend Total | calculated | ✅ Корректно |

**Файл**: `reports/eda/metrics_overall.json`

---

### 2. Метрики по Source/Campaign

**Scope**: Агрегация по источникам рекламы

| Метрика | Формула | Статус |
|---------|---------|--------|
| **Spend by Source** | SUM(spend) GROUP BY source | ✅ Корректно |
| **Deals by Source** | COUNT(deals) GROUP BY source | ✅ Корректно |
| **Paid Deals by Source** | COUNT(paid_deals) GROUP BY source | ✅ Корректно |
| **CPL by Source** | Spend / Deals (per source) | ✅ Корректно |
| **CPA by Source** | Spend / Paid Deals (per source) | ✅ Корректно |
| **ROAS by Source** | Revenue / Spend (per source) | ✅ Корректно |
| **Paid Rate by Source** | Paid Deals / Deals (per source) | ✅ Корректно |

**Файл**: `reports/eda/tables/ads_by_source.csv`

**Обоснование**: Данные Spend и Deals имеют общие поля `source` и `campaign`, поэтому метрики корректно аллоцируются на уровне источника.

---

### 3. Метрики по Sales Owner

**Scope**: Эффективность продажников

| Метрика | Формула | Статус |
|---------|---------|--------|
| **Deals by Owner** | COUNT(deals) GROUP BY deal_owner_name | ✅ Корректно |
| **Paid Deals by Owner** | COUNT(paid_deals) GROUP BY deal_owner_name | ✅ Корректно |
| **Paid Rate by Owner** | Paid Deals / Deals (per owner) | ✅ Корректно |
| **Revenue by Owner** | SUM(revenue) GROUP BY deal_owner_name | ✅ Корректно |
| **SLA (median) by Owner** | MEDIAN(sla_minutes) GROUP BY deal_owner_name | ✅ Корректно |

**Файл**: `reports/eda/tables/sales_by_owner.csv`

**Обоснование**: Каждая сделка имеет `deal_owner_name`, нет проблем с аллокацией.

---

### 4. Временные метрики

**Scope**: Time-to-close, временные ряды

| Метрика | Формула | Статус |
|---------|---------|--------|
| **Time-to-Close (median)** | MEDIAN(closing_date - created_time) для paid | ✅ Корректно |
| **Time-to-Close (P90)** | PERCENTILE_90(lag_days) для paid | ✅ Корректно |
| **Coverage closing_date** | % paid deals с непустым closing_date | ✅ Корректно (60.72%) |
| **Daily Deals** | COUNT(deals) GROUP BY date | ✅ Корректно |
| **Daily Spend** | SUM(spend) GROUP BY date | ✅ Корректно |
| **Daily Paid Rate** | Daily Paid Deals / Daily Deals | ✅ Корректно |

**Файл**: `reports/time/paid_time_to_close_stats.json`, `reports/time/figures/`

**Оговорка**: Time-to-close считается только для 60.72% paid deals (у остальных нет closing_date).

---

### 5. Метрики по звонкам

**Scope**: Связь Calls ↔ Deals

| Метрика | Формула | Статус |
|---------|---------|--------|
| **Total Calls** | COUNT(calls) | ✅ Корректно |
| **Calls matched to Deals** | COUNT(calls WITH deal_id) | ✅ Корректно |
| **Coverage** | Calls matched / Total Calls | ✅ Корректно (95.78%) |
| **Avg Calls per Deal** | Total Calls / Deals with Calls | ✅ Корректно (17.5) |

**Файл**: `reports/calls_deals/coverage_stats.json`

**Оговорка**: ID контактов пришли как Excel-числа → могут быть неточности в джойне, но coverage 95.78% указывает на хорошее качество.

---

### 6. Дубликаты (Duplicate Lost)

**Scope**: Анализ влияния дубликатов на метрики

| Метрика | Формула | Статус |
|---------|---------|--------|
| **Duplicate Deals** | COUNT(deals WHERE lost_reason='Duplicate') | ✅ Корректно |
| **Lost Revenue from Duplicates** | SUM(revenue) from duplicate deals | ✅ Корректно |
| **Impact on Paid Rate** | (Duplicates / Total Deals) * 100% | ✅ Корректно (8%) |

**Файл**: `reports/eda/duplicate_lost_impact.json`

**Инсайт**: 8% сделок — дубликаты в Lost stage → need deduplication before SLA tracking.

---

## ⚠️ Ограниченные метрики

### 7. Метрики по продуктам

**Scope**: Продуктовая аналитика

| Метрика | Статус | Причина |
|---------|--------|---------|
| **Revenue by Product** | ✅ Корректно | Прямая сумма из paid deals |
| **AOV by Product** | ✅ Корректно | Revenue / Paid Deals (per product) |
| **Paid Deals by Product** | ✅ Корректно | Прямой подсчёт |
| **Paid Rate by Product** | ⚠️ Ограниченно | Нужно достаточно данных (min 80 deals) |
| **CPL by Product** | ❌ Нельзя | Нет данных о распределении spend на продукт |
| **CPA by Product** | ❌ Нельзя | Нет данных о распределении spend на продукт |
| **ROAS by Product** | ❌ Нельзя | Зависит от CPA, который нельзя посчитать |

**Файл**: `reports/eda/tables/product_unit_econ_paid_only.csv`

**Проблема**: 
- Spend агрегирован по `Source + Campaign`
- Deals известны по `Source + Campaign + Product`
- Один источник → РАЗНЫЕ продукты
- **НЕТ** данных о том, какой spend пришёлся на конкретный продукт

**См. подробности**: `reports/DISCLAIMER_PRODUCT_METRICS.md`

---

### 8. Метрики по сегментам (Payment Type, Education Type, City, Level of Deutsch)

**Scope**: Сегментация по различным атрибутам

| Метрика | Статус | Причина |
|---------|--------|---------|
| **Revenue by Segment** | ✅ Корректно | Прямая сумма из paid deals |
| **AOV by Segment** | ✅ Корректно | Revenue / Paid Deals (per segment) |
| **Paid Rate by Segment** | ⚠️ Ограниченно | Требует min 80 deals для стабильности |
| **CPL/CPA/ROAS by Segment** | ❌ Нельзя | Аналогично продуктам — нет аллокации spend |

**Файлы**: 
- `reports/segments/tables/paid_by_payment_type.csv`
- `reports/segments/tables/paid_by_education_type.csv`
- `reports/segments/tables/funnel_by_city_min80.csv`
- `reports/segments/tables/funnel_by_level_of_deutsch_min80.csv`

**Оговорка**: Для Paid Rate по сегментам используем фильтр min 80 deals для статистической значимости.

---

## 🔍 Метрики с оговорками

### Closing Date Coverage (60.72%)

**Проблема**: У 39.28% paid deals нет `closing_date`

**Влияние на метрики**:
- ✅ Не влияет: Revenue, AOV, Paid Rate, CPA, ROAS (используют все paid deals)
- ⚠️ Влияет: Time-to-Close (считается только для 60.72% с closing_date)

**Решение**: Явно указываем coverage в отчётах и презентациях.

---

### Contact ID (Excel-числа)

**Проблема**: ID контактов в Calls/Deals пришли как Excel-числа → потеря precision

**Влияние на метрики**:
- ✅ Не влияет: Все метрики кроме Calls-Deals link
- ⚠️ Влияет: Coverage Calls↔Deals может быть слегка завышена/занижена

**Решение**: 
- Используем округлённые ID (`contact_id_str`)
- Coverage 95.78% — высокая, значит метод работает
- Для точного джойна лучше использовать Deals ↔ Spend по source/campaign

---

## 📊 Рекомендации по использованию метрик

### Для анализа эффективности рекламы:
✅ Используйте метрики **по Source/Campaign**:
- CPL, CPA, ROAS, Paid Rate
- Spend, Deals, Paid Deals, Revenue

❌ НЕ используйте метрики **по Product** для оценки рекламы:
- Невозможно корректно аллоцировать spend

### Для продуктовой аналитики:
✅ Используйте:
- Revenue breakdown
- AOV comparison
- Volume (paid deals count)
- Share of revenue/paid deals

❌ НЕ используйте:
- CPA по продукту
- ROAS по продукту

### Для анализа продаж:
✅ Используйте метрики **по Sales Owner**:
- Paid Rate, Revenue, SLA
- Deals volume

✅ Используйте метрики **Time-to-Close**:
- Median, P90 lag days
- С оговоркой про coverage 60.72%

---

## 🎯 Итоговая валидация

**Проект прошёл валидацию метрик:**

✅ **90%+ метрик корректны**
⚠️ **10% имеют ограничения** (CPA/ROAS по продуктам/сегментам)
📝 **Все ограничения задокументированы**

**Ключевые достижения:**
1. ✅ Идентифицирована проблема с аллокацией spend на продукты
2. ✅ Создан disclaimer (`DISCLAIMER_PRODUCT_METRICS.md`)
3. ✅ Обновлены отчёты и презентации с оговорками
4. ✅ Dashboard показывает только корректные метрики
5. ✅ Все ограничения прозрачно коммуницированы

**Статус**: ✅ **Готово для сдачи**

---

**Дата валидации**: 2026-02-10  
**Проверено**: Phase 2 Quality Check  
**Результат**: ✅ All critical metrics validated
