# 🚀 План реализации недостающих функций

## 📋 Приоритетные задачи

### 1️⃣ История донатов (Высокий приоритет)

**Файлы для создания:**
- `bot/services/donation_history_service.py`
- `bot/handlers/donation_commands.py`

**База данных:**
```sql
CREATE TABLE donation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_tag TEXT NOT NULL,
    player_name TEXT,
    clan_tag TEXT NOT NULL,
    donations_sent INTEGER DEFAULT 0,
    donations_received INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_type TEXT DEFAULT 'daily'
);
```

**Команды:**
- `/donation_history @user [days]` - история донатов
- `/donation_stats #CLANTAG [period]` - статистика клана

---

### 2️⃣ Статистика за периоды (Высокий приоритет)

**Файлы для создания:**
- `bot/services/period_analytics_service.py`
- `bot/handlers/analytics_commands.py`

**Команды:**
- `/stats_period @user 7d` - статистика за период
- `/compare_periods @user week1 week2` - сравнение

---

### 3️⃣ Модуль ИИ (Средний приоритет)

**Файлы для создания:**
- `bot/integrations/ai_module.py`

**Конфигурация:**
```env
AI_MODULE_ENABLED=false
```

---

## 📊 Оценка времени

- История донатов: 3-4 дня
- Статистика за периоды: 2-3 дня
- Модуль ИИ: 1-2 дня
- Кастомизация приветствий: 1 день

**Итого:** 7-10 дней разработки
