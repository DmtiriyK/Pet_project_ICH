# ⚠️ Disclaimer: Ограничения метрик по продуктам

## Проблема аллокации расходов

### Что известно из данных:
- `Spend` агрегирован по `Source + Campaign`
- `Deals` (и paid deals) известны по `Source + Campaign + Product`
- Один Source/Campaign может генерировать лиды для **разных продуктов** одновременно

### Что это означает:

**Пример:**
```
Source: Instagram, Campaign: "Spring2024"
Spend: 10,000 €

Deals:
- Web Developer: 50 leads → 10 paid
- Digital Marketing: 100 leads → 20 paid
- UX/UI Design: 30 leads → 5 paid

Вопрос: Сколько из 10,000€ пришлось на каждый продукт?
Ответ: ❌ НЕИЗВЕСТНО из данных!
```

### Метрики, которые НЕЛЬЗЯ посчитать корректно по продукту:

❌ **CPA (Cost Per Acquisition)** = Spend / Paid Deals
   - Нужна аллокация spend на продукт
   - Без неё CPA будет одинаковый для всех (общий spend / paid по продукту)

❌ **CPL (Cost Per Lead)** = Spend / Deals
   - Аналогичная проблема

❌ **ROAS (Return On Ad Spend)** = Revenue / Spend
   - Зависит от аллокации spend

### Метрики, которые МОЖНО посчитать корректно:

✅ **Revenue (cash/contract)** по продукту
   - Прямая сумма из paid deals

✅ **AOV (Average Order Value)** = Revenue / Paid Deals  
   - Использует только revenue и paid deals данного продукта

✅ **Paid Rate** = Paid Deals / Deals
   - Воронка внутри продукта

✅ **Количество deals/paid deals** по продукту
   - Прямой подсчёт

## Возможные решения (с допущениями):

### Вариант 1: Пропорциональная аллокация по лидам
```python
# Для каждого Source/Campaign:
# Распределить spend пропорционально количеству лидов на каждый продукт

product_spend = total_spend * (product_leads / total_leads_in_source)
product_cpa = product_spend / product_paid_deals
```

**Допущение**: Стоимость лида одинаковая для всех продуктов внутри источника.  
**Риск**: Неверно, если один продукт дороже/дешевле в привлечении.

### Вариант 2: Пропорциональная аллокация по paid deals
```python
# Для каждого Source/Campaign:
product_spend = total_spend * (product_paid_deals / total_paid_deals_in_source)
product_cpa = product_spend / product_paid_deals  # всегда = avg_cpa_of_source
```

**Проблема**: CPA получается одинаковый внутри источника → бесполезно.

### Вариант 3: НЕ считать CPA/ROAS по продуктам
```python
# Признать ограничение данных
# Считать только: Revenue, AOV, Paid Rate, Volume
```

**Рекомендация**: Это **honest approach**. Лучше не считать, чем считать с сильными допущениями.

## Что делать в итоговом проекте:

### ✅ Рекомендуемый подход:

1. **Явно указать ограничение** в README и отчёте:
   ```markdown
   ⚠️ CPA/ROAS по продукту не считаются из-за отсутствия данных 
   о распределении spend между продуктами внутри одного источника.
   ```

2. **Сфокусироваться на доступных метриках**:
   - Revenue breakdown по продуктам (paid-only)
   - AOV comparison
   - Volume (paid deals count)
   - Share of revenue/paid deals

3. **CPA/ROAS считать только на уровне Source/Campaign**:
   - Там корректная привязка Spend ↔ Deals ↔ Paid

### 📊 Таблица по продуктам (корректная):

| Product | Paid Deals | Revenue (Contract) | AOV | Share of Revenue |
|---------|------------|-------------------|-----|-----------------|
| Digital Marketing | 474 | 3,892,400 € | 8,212 € | 65% |
| UX/UI Design | 229 | 1,831,500 € | 7,998 € | 31% |
| Web Developer | 137 | 571,500 € | 4,172 € | 10% |

**Insights:**
- Digital Marketing — самый популярный (65% revenue)
- UX/UI Design — второй по объёму (31% revenue)
- Web Developer — меньший AOV (4,172€ vs 8,212€)

## Выводы:

1. **Не пытаться считать CPA/ROAS по продуктам** без дополнительных данных
2. **Честно признать ограничение** в отчёте/презентации
3. **Рекомендация для будущего**: добавить в CRM поле "Target Product" в рекламных кампаниях
4. **Фокус на корректных метриках**: Revenue, AOV, Volume, Paid Rate по продуктам

---

**Дата создания**: 2026-02-10  
**Автор**: Phase 2 Quality Check  
**Статус**: ⚠️ Critical limitation documented
