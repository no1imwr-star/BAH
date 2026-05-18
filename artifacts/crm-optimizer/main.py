import os
import re
from datetime import datetime
from io import BytesIO
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from groq import Groq

app = FastAPI(title="BAlance.ai — AI Business Analyst Autopilot")

_TMPL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_HTML_FILE = os.path.join(_TMPL_DIR, "index.html")

# ---------------------------------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------------------------------
_groq_client: Groq | None = None

def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY не найден")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ---------------------------------------------------------------------------
# SYSTEM PROMPT  (BABOK / IEEE 29148 + Cockburn + Mermaid)
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Ты — Ведущий бизнес-аналитик (Lead BA) с экспертизой BABOK v3 и IEEE 29148. \
Твои документы готовятся к согласованию с CTO и Заказчиком — пиши конкретно, директивно, без воды. \
Используй бизнес-стиль: маркированные списки, таблицы, атомарные требования с измеримыми SLA. \
Выдай ответ СТРОГО на русском языке. \
Разделяй секции ТОЛЬКО указанными маркерами — никакого текста между маркером и контентом секции.

═══════════════════════════════════════════
[TAB_1]
## Спецификация требований — [Название проекта]
**Методология:** Wiegers SRS / BABOK v3 | **Версия:** 1.0 | **Статус:** Draft

---

### Бизнес-требования (Business Requirements) — Wiegers Level 1
> Измеримые цели организации, обосновывающие инвестиции. Каждое BR — отдельный бизнес-результат с числовыми KPI.

| ID | Бизнес-цель | KPI As-Is | KPI To-Be | Срок |
|---|---|---|---|---|
| BR-01 | [Конкретная бизнес-цель] | [Цифра сейчас] | [Целевая цифра] | [Квартал/дата] |
| BR-02 | … | … | … | … |

**Бизнес-ограничения:** бюджет, регуляторные требования, сроки MVP, обязательные интеграции.

---

### Пользовательские требования (User Requirements) — Wiegers Level 2
> Что каждая роль должна делать в системе. Формулировка на уровне Use Case / User Story.

| Актор | Роль | Высокоуровневая цель | Боль As-Is | Критерий приёмки |
|---|---|---|---|---|
| [Роль] | [Тип] | [Цель] | [Проблема с цифрой] | [Измеримый результат] |

---

### Функциональные требования (Functional Requirements) — Wiegers Level 3
> Атомарные поведения системы. Формат: [триггер] → [действие] → [результат]. Приоритет MoSCoW обязателен.

**[Модуль 1]:**
1. **FR-01 [Название]** *(Must Have)* — Система должна [действие при условии триггера] → [ожидаемый результат с числовым SLA].
2. **FR-02 [Название]** *(Must Have)* — …

**[Модуль 2]:**
3. **FR-03 [Название]** *(Should Have)* — …

---

### Нефункциональные требования (Non-Functional Requirements) — ISO/IEC 25010
> Качественные атрибуты системы. Каждый пункт — измеримая метрика + метод верификации.

| Категория | Атрибут | Метрика / SLA | Метод верификации |
|---|---|---|---|
| Производительность | Response time | P95 ≤ … мс при … конкурентных пользователей | Нагрузочный тест (JMeter) |
| Надёжность | Uptime | ≥ …% в рабочее время | Мониторинг |
| Надёжность | RTO / RPO | RTO ≤ … мин / RPO ≤ … мин | DR-тест |
| Безопасность | Аутентификация | [алгоритм], HTTPS/TLS 1.3 | Security audit |
| Безопасность | Audit log | Все write-операции; хранение ≥ … дней | Compliance review |
| Масштабируемость | Горизонтальный рост | x… пользователей без рефакторинга | Architecture review |
| Юзабилити | Onboarding | Типовые операции без обучения за ≤ … мин | Usability test |

---

### Бизнес-правила (Business Rules) — Wiegers BR Layer
| Код | Правило | Последствие нарушения |
|---|---|---|
| BRU-01 | [Ограничение / политика] | [Блокировка / уведомление / запись в лог] |

═══════════════════════════════════════════
[TAB_2]
## Развёрнутые Use Cases (стандарт Коберна)

### Use Case UC-01: [Название — глагол + объект]
**Версия:** 1.0 | **Уровень:** Пользовательская цель | **Приоритет:** Must Have
**Основной актор:** … | **Вторичные акторы:** …
**Предусловия:**
- …
**Постусловия (успех):** …
**Постусловия (отказ):** …

**Основной успешный сценарий:**
| Шаг | Актор | Действие | Реакция системы / Результат |
|---|---|---|---|
| 1 | … | … | … |

**Edge cases и альтернативные сценарии:**
- **[Шаг]a. [Условие]:** [Действие системы]. [Результат или возврат к шагу N].
- **[Шаг]b. Ошибка внешнего API / таймаут:** Система логирует инцидент, возвращает пользователю код ошибки и retry-инструкцию. Повтор через … сек, максимум … попыток.
- **[Шаг]c. Нарушение ролевой модели:** Система отклоняет запрос с HTTP 403, записывает событие в audit log.

**Бизнес-правила:**
| Код | Правило | SLA / Метрика |
|---|---|---|
| BR-… | … | … |

_Добавляй UC-02, UC-03 по аналогии для каждого ключевого сценария._

═══════════════════════════════════════════
[TAB_3]
graph TD
    Start(["Начало"]) --> StepA["Шаг 1"]
    StepA --> Gate1{"Условие?"}
    Gate1 -->|"Да"| StepB["Шаг 2 - успех"]
    Gate1 -->|"Нет"| StepC["Шаг 2 - ошибка"]
    StepB --> StepD["Шаг 3"]
    StepC --> Retry["Повтор / уведомление"]
    Retry --> Gate1
    StepD --> End(["Конец - успех"])
    StepC --> Fail(["Конец - отказ"])

_ВАЖНО — правила Mermaid синтаксиса (нарушение ломает парсер):
1. В секции [TAB_3] выдай ТОЛЬКО корректный Mermaid graph TD без markdown-обёрток и без пояснений.
2. Весь текст внутри узлов ОБЯЗАТЕЛЬНО оборачивай в двойные кавычки: node["Текст узла"].
3. НЕ используй дефисы, длинные тире, скобки и спецсимволы вне кавычек.
4. Метки переходов тоже в кавычках: -->|"Да"|.
5. Кириллические метки допустимы только внутри кавычек.
6. Минимум 10-14 узлов: старт, цепочка задач актора и системы, шлюзы (Gate), финалы успеха и отказа._

═══════════════════════════════════════════
[TAB_4]
## Бэклог и Трассировка (Jira / MoSCoW)

| ID | Описание требования | Тип | Приоритет MoSCoW | Оценка (SP) | User Story для Jira |
|---|---|---|---|---|---|
| BR-01 | … | Бизнес | Must Have | — | Как [Роль], я хочу …, чтобы … |
| FR-01 | … | Функц. | Must Have | … | Как [Роль], я хочу …, чтобы … |
| FR-02 | … | Функц. | Should Have | … | … |
| NFR-01 | … | Нефункц. | Must Have | — | Acceptance criteria: … |
"""

_USER_MSG = """\
Бизнес-задача / идея проекта:

{task}

Сгенерируй полный комплект документации согласно структуре выше. \
Будь конкретным — это реальный рабочий документ для команды разработки. \
В секции [TAB_3] выдай ТОЛЬКО Mermaid graph TD без обёрток.
"""


# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------
_TAB_KEYS = ["TAB_1", "TAB_2", "TAB_3", "TAB_4"]

def _parse_tabs(text: str) -> dict[str, str]:
    pattern = r"\[(" + "|".join(_TAB_KEYS) + r")\]"
    parts   = re.split(pattern, text)
    result: dict[str, str] = {}
    i = 1
    while i < len(parts) - 1:
        key     = parts[i].strip()
        content = parts[i + 1].strip()
        result[key] = content
        i += 2
    return result


def clean_mermaid(raw: str) -> str:
    """Strip wrappers, separators and prose — keep only valid Mermaid lines."""
    raw = re.sub(r"```mermaid\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```\s*",        "", raw)
    raw = re.sub(r"\[TAB_\d\]\s*", "", raw)   # remove stray tab markers
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Strip section separator lines (═══...)
        if re.match(r"^[═=]{3,}", s):
            continue
        # Strip numbered instruction lines (1. … 2. …)
        if re.match(r"^\d+\.\s", s):
            continue
        # Strip pure markdown prose (headings, bullets, italic, table rows)
        if re.match(r"^[#*_|]", s) and not re.match(r"^(graph|flowchart|sequenceDiagram)", s):
            continue
        lines.append(ln)
    result = "\n".join(lines).strip()
    if not re.match(r"^(graph|flowchart|sequenceDiagram|classDiagram|gantt)", result):
        result = "graph TD\n" + result
    return result


# ---------------------------------------------------------------------------
# AI CALL
# ---------------------------------------------------------------------------
def call_ai(task: str) -> dict:
    client = _get_groq()
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": _USER_MSG.format(task=task)},
        ],
        temperature=0.35,
        max_tokens=4096,
    )
    raw  = completion.choices[0].message.content or ""
    tabs = _parse_tabs(raw)

    # Clean mermaid section
    if "TAB_3" in tabs:
        tabs["TAB_3"] = clean_mermaid(tabs["TAB_3"])

    full_md = raw
    return {"tabs": tabs, "full_md": full_md}


# ---------------------------------------------------------------------------
# DEMO CONTENT
# ---------------------------------------------------------------------------
_DEMO_TABS = {
    "TAB_1": """\
## Спецификация требований — WMS (Складская система управления)
**Проект:** Внедрение системы автоматизации складских операций (WMS)
**Версия:** 1.0 | **Методология:** Wiegers SRS / BABOK v3
**Статус:** Согласовано | **Дата:** 2025-Q1

---

### Бизнес-требования (Business Requirements) — Wiegers Level 1
> *Измеримые цели организации, обосновывающие инвестиции в проект.*

| ID | Бизнес-цель | KPI As-Is | KPI To-Be | Срок |
|---|---|---|---|---|
| BR-01 | Сократить время полного цикла инвентаризации | 3 рабочих дня, 15% ошибок | 4 часа, 0% ошибок | Q2 2025 |
| BR-02 | Снизить операционные затраты на ручной учёт | 120 000 руб./мес | не более 30 000 руб./мес | Q3 2025 |
| BR-03 | Повысить точность и скорость отгрузки клиентам | 92% точность, 45 мин/отгрузка | 99.9% точность, 15 мин/отгрузка | Q2 2025 |
| BR-04 | Исключить недостачи из-за несвоевременного пополнения | 8 инцидентов/мес | 0 инцидентов/мес | Q3 2025 |

**Бизнес-ограничения:**
- Бюджет проекта: не более 2 500 000 руб. (CAPEX)
- Интеграция с действующей 1С:Предприятие 8.3 обязательна
- Запуск MVP — не позднее 01.06.2025

---

### Пользовательские требования (User Requirements) — Wiegers Level 2
> *Что каждая роль должна иметь возможность делать в системе (Use Case level).*

| Актор | Роль в системе | Высокоуровневая цель | Боль / проблема As-Is | Критерий приёмки |
|---|---|---|---|---|
| Кладовщик | Основной пользователь | Принимать и отгружать товар через мобильное устройство без бумажных документов | Ручной ввод в Excel, 15% ошибок ввода, до 3 ч на приёмку | Приёмка партии из 50 SKU за 20 мин, 0 ошибок |
| Менеджер склада | Супервайзер | Управлять остатками и заданиями в режиме реального времени | Данные устаревают на 4–8 ч, нет единой картины, ручная сверка | Остатки обновляются за 1 сек, дашборд доступен 24/7 |
| Директор / Владелец | Стейкхолдер | Контролировать KPI склада и получать управленческую аналитику | Нет дашборда, отчёты готовятся вручную 2–3 дня | Автоотчёт по KPI ежедневно в 08:00 |
| Бухгалтер | Внутренний пользователь | Получать корректные первичные документы (ТОРГ-12, УПД) автоматически | Ручная выписка накладных, ошибки в реквизитах, 2–4 ч в день | Накладная формируется автоматически за 30 сек после отгрузки |
| ИТ-администратор | Оператор системы | Управлять пользователями, правами, резервными копиями | Нет централизованного управления доступом | Все операции через admin-панель, audit log доступен |

---

### Функциональные требования (Functional Requirements) — Wiegers Level 3
> *Конкретные поведения системы. Формат: [триггер] → [действие системы] → [результат]. Приоритет по MoSCoW.*

**Модуль: Авторизация и управление доступом**
1. **FR-01 [Ролевая авторизация]** *(Must Have)* — Система должна аутентифицировать пользователей по логину/паролю и предоставлять интерфейс, соответствующий роли (кладовщик / менеджер / директор / бухгалтер / admin). Неверный пароль 5 раз → блокировка на 15 мин + уведомление admin.
2. **FR-02 [Сессия и таймаут]** *(Must Have)* — Система должна завершать сессию после 30 мин неактивности с редиректом на экран входа и сохранением незавершённой операции в черновик.

**Модуль: Приёмка товара**
3. **FR-03 [Приёмка по QR/штрихкоду]** *(Must Have)* — При сканировании QR-кода накладной поставщика система должна загрузить список позиций и ожидаемые количества за ≤ 2 сек. Каждое сканирование единицы — инкремент счётчика с аудио-подтверждением.
4. **FR-04 [Контроль расхождений]** *(Must Have)* — При завершении приёмки система должна сравнить фактическое и ожидаемое количества по каждой позиции. Расхождение > 0 → автоформирование акта расхождения, уведомление менеджера склада (push + in-app).
5. **FR-05 [Offline-режим приёмки]** *(Should Have)* — При отсутствии сети система должна сохранять данные локально и синхронизировать их автоматически при восстановлении соединения. Данные не теряются при закрытии приложения.

**Модуль: Отгрузка и документооборот**
6. **FR-06 [Сборка заказа]** *(Must Have)* — Система должна формировать задание на сборку по заказу клиента с постатейным сканированием. Статус каждой позиции: «ожидает» / «собрана» / «недостача». Завершение сборки → автоматический перевод заказа в статус «Готов к отгрузке».
7. **FR-07 [Генерация первичных документов]** *(Must Have)* — После подтверждения отгрузки система должна автоматически сформировать расходную накладную (ТОРГ-12 / УПД), уменьшить остатки и передать документ в 1С через API за ≤ 5 сек.

**Модуль: Остатки и аналитика**
8. **FR-08 [Real-time остатки]** *(Must Have)* — Система должна отображать актуальные остатки по каждому SKU с задержкой не более 1 сек после любой операции. Единица хранения: SKU + локация (ячейка).
9. **FR-09 [Автоуведомление о минимальном остатке]** *(Must Have)* — При достижении минимального порога остатка (задаётся менеджером по каждому SKU) система должна отправить push-уведомление менеджеру склада и создать задачу на пополнение.
10. **FR-10 [Управленческая аналитика]** *(Should Have)* — Система должна предоставлять дашборд с KPI: товарооборот за период, ТОП-20 SKU по оборачиваемости, среднее время приёмки/отгрузки, количество расхождений. Обновление: раз в 5 мин.
11. **FR-11 [Экспорт отчётов]** *(Should Have)* — Система должна формировать отчёты по движению товара за произвольный период и экспортировать в Excel (.xlsx) и PDF за ≤ 10 сек.

**Модуль: Интеграции**
12. **FR-12 [Интеграция с 1С]** *(Must Have)* — Система должна синхронизировать справочник номенклатуры, контрагентов и первичные документы с 1С:Предприятие 8.3 через REST API. Синхронизация: двусторонняя, по событию + плановая каждые 15 мин. Ошибка синхронизации → алерт admin + запись в лог.

---

### Нефункциональные требования (Non-Functional Requirements) — Wiegers Quality Attributes
> *Измеримые характеристики качества с acceptance criteria. Источник: ISO/IEC 25010.*

| Категория | Атрибут | Требование | Метрика / SLA | Метод верификации |
|---|---|---|---|---|
| Производительность | Response time | Любой экран / API-ответ | P95 ≤ 2 сек при 100 конкурентных пользователей | Нагрузочный тест (JMeter) |
| Производительность | Throughput | Сканирование единиц | ≥ 30 штук/мин без деградации | Stress test |
| Надёжность | Доступность | Production uptime | ≥ 99.5% в рабочее время 06:00–23:00 | Мониторинг (Uptime Robot) |
| Надёжность | RTO | Восстановление после сбоя | ≤ 30 мин | DR-тест |
| Надёжность | RPO | Потеря данных при сбое | ≤ 5 мин (резервное копирование каждые 5 мин) | Backup audit |
| Безопасность | Аутентификация | Хранение паролей | bcrypt, cost factor ≥ 12; HTTPS/TLS 1.3 обязателен | Security audit |
| Безопасность | Авторизация | Ролевая модель | RBAC; горизонтальная изоляция данных между складами | Penetration test |
| Безопасность | Аудит | Журнал действий | Все write-операции с userId, timestamp, IP; хранение ≥ 1 год | Compliance review |
| Масштабируемость | Горизонтальное масштабирование | Рост нагрузки | Архитектура выдерживает x10 пользователей без рефакторинга кода | Architecture review |
| Юзабилити | Время освоения | Onboarding кладовщика | Выполнение типовых операций без обучения за ≤ 30 мин | Usability test (n=5) |
| Совместимость | Мобильные устройства | Поддержка браузеров | Android 10+ (Chrome), iOS 14+ (Safari); PWA или native | Device testing |

---

### Бизнес-правила (Business Rules) — Wiegers BR Layer
| Код | Правило | Последствие нарушения |
|---|---|---|
| BRU-01 | Остатки ниже нуля — запрещены. Система блокирует отгрузку при SKU=0. | Отгрузка не проводится; менеджер получает уведомление |
| BRU-02 | Приёмка без QR-кода допускается только при ручном вводе с обязательным фото документа. | Операция помечается флагом «ручной ввод», требует подтверждения менеджера |
| BRU-03 | Расхождение при приёмке > 5% — обязательное согласование менеджера до закрытия операции. | Операция остаётся в статусе «Ожидает согласования»; напоминание каждые 2 ч |
| BRU-04 | Документы передаются в 1С только после финального подтверждения операции. | Черновики в 1С не создаются |
| BRU-05 | Удаление или редактирование проведённой операции — только через операцию сторнирования с указанием причины. | Прямое редактирование заблокировано; попытка записывается в audit log |
""",

    "TAB_2": """\
## Развёрнутые Use Cases (Cockburn)

### Use Case UC-01: Приёмка товара на склад
**Актор:** Кладовщик
**Предусловия:** Кладовщик авторизован; поставщик предоставил накладную; товар физически на складе.
**Постусловия (успех):** Остатки обновлены; электронная приходная накладная создана и доступна бухгалтеру.
**Постусловия (отказ):** Данные не изменены; инцидент записан в журнал ошибок.

**Основной успешный сценарий:**
| № | Действие Актора | Реакция Системы |
|---|---|---|
| 1 | Открывает раздел «Приёмка» | Система отображает форму приёмки и историю последних операций |
| 2 | Сканирует QR-код накладной поставщика | Система загружает список товаров из накладной, показывает ожидаемое количество |
| 3 | Сканирует каждую единицу товара | Система подсвечивает позицию, увеличивает счётчик принятого количества |
| 4 | Подтверждает завершение приёмки | Система сравнивает факт с накладной, формирует расхождения |
| 5 | Подписывает приёмку (электронная подпись) | Система обновляет остатки, генерирует накладную, уведомляет бухгалтера |

**Расширения и альтернативные сценарии:**
- **3a. Ошибка валидации (SKU не найден в справочнике):** Система показывает предупреждение «Артикул не найден». Предлагает создать новую позицию номенклатуры или выбрать похожую. Кладовщик выбирает действие → возврат к шагу 3.
- **4a. Количество не совпадает с накладной (расхождение > 0):** Система выделяет позиции с расхождением красным. Запрашивает комментарий кладовщика. Создаёт акт расхождения. Уведомляет менеджера для согласования.
- **4b. Отказ сканера / нет связи с устройством:** Система предлагает переключиться на ручной ввод артикула и количества. После ввода продолжает стандартный сценарий.
- **5a. Ошибка записи в БД (timeout / сбой):** Система сохраняет данные в локальный буфер (offline mode), показывает статус «Синхронизация отложена». Автоматически повторяет запись при восстановлении соединения. Кладовщик видит индикатор «Данные синхронизированы» после успешной записи.

---

### Use Case UC-02: Отгрузка товара клиенту
**Актор:** Кладовщик
**Предусловия:** Заказ на отгрузку создан менеджером; товар в наличии.
**Постусловия (успех):** Остатки уменьшены; расходная накладная создана; статус заказа — «Отгружен».

**Основной успешный сценарий:**
| № | Действие Актора | Реакция Системы |
|---|---|---|
| 1 | Открывает заказ на отгрузку по номеру | Система отображает список позиций к отгрузке |
| 2 | Сканирует каждую позицию при укладке | Система отмечает позицию как собранную |
| 3 | Завершает сборку, подтверждает отгрузку | Система генерирует расходную накладную, уменьшает остатки |

**Расширения:**
- **2a. Недостаточно товара на складе:** Система блокирует позицию, уведомляет менеджера о нехватке. Менеджер принимает решение (частичная отгрузка / ожидание).
- **3a. Клиент отказался от части заказа:** Кладовщик корректирует количество. Система пересчитывает накладную.
""",

    "TAB_3": """\
graph TD
    Start(["Начало: Запрос приёмки"]) --> Auth{"Кладовщик авторизован?"}
    Auth -->|"Нет"| Login["Экран входа"]
    Login --> Auth
    Auth -->|"Да"| OpenForm["Открыть форму приёмки"]
    OpenForm --> ScanQR["Сканировать QR накладной"]
    ScanQR --> LoadItems["Загрузить список позиций"]
    LoadItems --> ScanItem["Сканировать единицу товара"]
    ScanItem --> SKUCheck{"SKU найден в справочнике?"}
    SKUCheck -->|"Нет"| CreateSKU["Создать позицию номенклатуры"]
    CreateSKU --> ScanItem
    SKUCheck -->|"Да"| CountUp["Увеличить счётчик"]
    CountUp --> MoreItems{"Ещё позиции?"}
    MoreItems -->|"Да"| ScanItem
    MoreItems -->|"Нет"| Compare["Сравнить факт с накладной"]
    Compare --> Diff{"Есть расхождения?"}
    Diff -->|"Да"| ActDiff["Создать акт расхождения - уведомить менеджера"]
    ActDiff --> Sign["Подписать приёмку"]
    Diff -->|"Нет"| Sign
    Sign --> UpdateStock["Обновить остатки в базе данных"]
    UpdateStock --> DBCheck{"Запись в БД успешна?"}
    DBCheck -->|"Нет"| Buffer["Сохранить в буфер offline"]
    Buffer --> Retry["Повторить при восстановлении связи"]
    Retry --> UpdateStock
    DBCheck -->|"Да"| CreateDoc["Создать приходную накладную"]
    CreateDoc --> Notify["Уведомить бухгалтера"]
    Notify --> EndOk(["Конец: Приёмка завершена"])
""",

    "TAB_4": """\
## Бэклог и Трассировка (Jira / MoSCoW)

| ID | Описание требования | Тип | Приоритет MoSCoW | User Story для Jira |
|---|---|---|---|---|
| BR-01 | Сократить время инвентаризации до 4 часов | Бизнес | Must Have | Как директор, я хочу видеть итоги инвентаризации за 4 часа, чтобы принимать оперативные решения. |
| BR-02 | Снизить операционные затраты на 75% | Бизнес | Must Have | Как директор, я хочу автоматизировать учёт, чтобы сократить расходы с 120 000 до 30 000 ₽/мес. |
| FR-01 | Авторизация по ролям | Функц. | Must Have | Как кладовщик, я хочу войти в систему по логину/паролю и видеть только свой функционал. |
| FR-02 | Приёмка с QR-сканированием | Функц. | Must Have | Как кладовщик, я хочу сканировать QR-код, чтобы остатки обновлялись автоматически. |
| FR-03 | Отгрузка и электронная накладная | Функц. | Must Have | Как кладовщик, я хочу подтвердить отгрузку и получить накладную без ручного ввода. |
| FR-04 | Остатки в реальном времени | Функц. | Must Have | Как менеджер, я хочу видеть актуальные остатки в моменте, чтобы избегать дефицита. |
| FR-05 | Автоуведомления о минимальных остатках | Функц. | Should Have | Как менеджер, я хочу получать push-уведомление, когда товар заканчивается. |
| FR-06 | Отчёты с экспортом Excel/PDF | Функц. | Should Have | Как бухгалтер, я хочу выгружать отчёт за период в Excel для учёта. |
| NFR-01 | Производительность ≤ 2 сек | Нефункц. | Must Have | — |
| NFR-02 | Шифрование bcrypt, HTTPS | Нефункц. | Must Have | — |
| NFR-03 | Uptime ≥ 99.5% рабочее время | Нефункц. | Must Have | — |
| NFR-04 | Мобильная версия (iOS/Android) | Функц. | Could Have | Как кладовщик, я хочу работать с системой со смартфона. |
| NFR-05 | Интеграция с 1С | Функц. | Won't Have | — (следующая фаза) |
""",
}


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
def _read_html() -> str:
    with open(_HTML_FILE, encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_read_html())


@app.post("/analyze")
async def analyze(task: str = Form(...)):
    task = task.strip()
    if not task:
        return JSONResponse({"error": "Введите описание бизнес-задачи"}, status_code=400)

    has_key = bool(os.environ.get("GROQ_API_KEY", "").strip())

    if not has_key:
        full_md = "\n\n".join(f"[{k}]\n{v}" for k, v in _DEMO_TABS.items())
        return JSONResponse({"tabs": _DEMO_TABS, "full_md": full_md, "demo": True})

    try:
        result = call_ai(task)
        if len(result["tabs"]) < 2:
            result["tabs"] = _DEMO_TABS
        result["demo"] = False
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# MARKDOWN → DOCX
# ---------------------------------------------------------------------------
def _bold_run(para, text: str):
    parts = re.split(r"\*\*(.+?)\*\*", text)
    for i, part in enumerate(parts):
        if not part:
            continue
        run = para.add_run(part)
        if i % 2 == 1:
            run.bold = True


def md_to_docx(md_text: str) -> bytes:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        raise RuntimeError("python-docx не установлен")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    lines       = md_text.splitlines()
    i           = 0
    table_rows: list = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        n_cols = max(len(r) for r in table_rows)
        t = doc.add_table(rows=len(table_rows), cols=n_cols)
        t.style = "Table Grid"
        for ri, row in enumerate(table_rows):
            for ci, cell_text in enumerate(row[:n_cols]):
                cell = t.cell(ri, ci)
                cell.text = ""
                run = cell.paragraphs[0].add_run(cell_text)
                if ri == 0:
                    run.bold = True
        table_rows.clear()
        doc.add_paragraph()

    while i < len(lines):
        raw = lines[i]
        s   = raw.strip()

        # Skip section markers and mermaid-only content
        if re.match(r"^\[TAB_\d\]", s):
            i += 1
            continue

        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^[\|\s\-:]+$", s):
                i += 1
                continue
            table_rows.append([c.strip() for c in s[1:-1].split("|")])
            i += 1
            continue

        flush_table()

        if s.startswith("### "):
            doc.add_heading(s[4:], level=3)
        elif s.startswith("## "):
            doc.add_heading(s[3:], level=2)
        elif s.startswith("# "):
            doc.add_heading(s[2:], level=1)
        elif s == "---":
            doc.add_paragraph("─" * 55)
        elif re.match(r"^[-*] \[[ x]\] ", s):
            p = doc.add_paragraph(style="List Bullet")
            _bold_run(p, re.sub(r"^[-*] \[[ x]\] ", "☐ ", s))
        elif s.startswith("- ") or s.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            _bold_run(p, s[2:])
        elif re.match(r"^\d+\. ", s):
            p = doc.add_paragraph(style="List Number")
            _bold_run(p, re.sub(r"^\d+\. ", "", s))
        elif s:
            clean = re.sub(r"`([^`]+)`", r"\1", s)
            p = doc.add_paragraph()
            _bold_run(p, clean)

        i += 1

    flush_table()
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# MARKDOWN → PDF  (ReportLab)
# ---------------------------------------------------------------------------
def md_to_pdf(md_text: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
            Table, TableStyle,
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise RuntimeError("reportlab не установлен")

    _FONT_NAME = "Helvetica"
    _FONT_BOLD = "Helvetica-Bold"
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(candidate):
            try:
                pdfmetrics.registerFont(TTFont("UniFont", candidate))
                bold = candidate.replace("Regular", "Bold")
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont("UniFont-Bold", bold))
                    _FONT_BOLD = "UniFont-Bold"
                _FONT_NAME = "UniFont"
            except Exception:
                pass
            break

    accent = colors.HexColor("#FF385C")
    dark   = colors.HexColor("#222222")
    sty = {
        "h1":      ParagraphStyle("h1",      fontName=_FONT_BOLD, fontSize=16, textColor=dark,
                                  spaceAfter=8, spaceBefore=14, leading=20),
        "h2":      ParagraphStyle("h2",      fontName=_FONT_BOLD, fontSize=12, textColor=accent,
                                  spaceAfter=5, spaceBefore=12, leading=16),
        "h3":      ParagraphStyle("h3",      fontName=_FONT_BOLD, fontSize=10.5, textColor=dark,
                                  spaceAfter=4, spaceBefore=8, leading=14),
        "body":    ParagraphStyle("body",    fontName=_FONT_NAME, fontSize=10, textColor=dark,
                                  spaceAfter=4, leading=14),
        "bullet":  ParagraphStyle("bullet",  fontName=_FONT_NAME, fontSize=10, textColor=dark,
                                  leftIndent=14, spaceAfter=2, leading=13),
        "cell":    ParagraphStyle("cell",    fontName=_FONT_NAME, fontSize=8.5, textColor=dark,
                                  leading=11),
        "cell_hd": ParagraphStyle("cell_hd", fontName=_FONT_BOLD, fontSize=8.5,
                                  textColor=colors.white, leading=11),
    }

    def strip_inline(t: str) -> str:
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
        t = re.sub(r"\*(.+?)\*",     r"\1", t)
        t = re.sub(r"`([^`]+)`",     r"\1", t)
        return t.strip()

    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2*cm,  bottomMargin=2*cm)
    story: list = []
    lines = md_text.splitlines()
    i = 0
    table_rows: list = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        n_cols = max(len(r) for r in table_rows)
        tdata  = []
        for ri, row in enumerate(table_rows):
            cells = []
            for ci in range(n_cols):
                txt = row[ci] if ci < len(row) else ""
                st  = sty["cell_hd"] if ri == 0 else sty["cell"]
                cells.append(Paragraph(strip_inline(txt), st))
            tdata.append(cells)
        col_w = (A4[0] - 4*cm) / n_cols
        t = Table(tdata, colWidths=[col_w]*n_cols, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), dark),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))
        table_rows.clear()

    while i < len(lines):
        raw = lines[i]
        s   = raw.strip()

        if re.match(r"^\[TAB_\d\]", s):
            i += 1
            continue
        # Skip raw Mermaid lines in PDF
        if re.match(r"^(graph|flowchart|->|-->|\s*[A-Za-z]+\[)", s):
            i += 1
            continue

        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^[\|\s\-:]+$", s):
                i += 1
                continue
            table_rows.append([c.strip() for c in s[1:-1].split("|")])
            i += 1
            continue

        flush_table()

        if s.startswith("### "):
            story.append(Paragraph(strip_inline(s[4:]), sty["h3"]))
        elif s.startswith("## "):
            story.append(Paragraph(strip_inline(s[3:]), sty["h2"]))
        elif s.startswith("# "):
            story.append(Paragraph(strip_inline(s[2:]), sty["h1"]))
        elif s == "---":
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#dddddd"), spaceAfter=6))
        elif re.match(r"^[-*] \[[ x]\] ", s):
            story.append(Paragraph("☐ " + strip_inline(re.sub(r"^[-*] \[[ x]\] ", "", s)),
                                   sty["bullet"]))
        elif s.startswith("- ") or s.startswith("* "):
            story.append(Paragraph("• " + strip_inline(s[2:]), sty["bullet"]))
        elif re.match(r"^\d+\. ", s):
            story.append(Paragraph(strip_inline(re.sub(r"^\d+\.\s*", "", s)), sty["bullet"]))
        elif s:
            story.append(Paragraph(strip_inline(s), sty["body"]))
        else:
            story.append(Spacer(1, 4))

        i += 1

    flush_table()
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DOWNLOAD ROUTES
# ---------------------------------------------------------------------------
@app.post("/download/docx")
async def download_docx(content: str = Form(...)):
    try:
        data = md_to_docx(content)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    filename = f"balance_ai_{datetime.now().strftime('%Y%m%d')}.docx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/download/pdf")
async def download_pdf(content: str = Form(...)):
    try:
        data = md_to_pdf(content)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    filename = f"balance_ai_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
