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
## Пирамида требований (BR / UR / FR / NFR)

### Бизнес-требования (Business Requirements)
Глобальные цели организации с измеримыми KPI. Каждое BR — отдельный бизнес-результат.
- **BR-01 [Название]:** Описание цели.
  - KPI As-Is: … (конкретная цифра)
  - KPI To-Be: … (конкретная цифра + срок)
- **BR-02 [Название]:** …

### Пользовательские требования (User Requirements)
Роли (акторы), их цели и текущие боли. Только реальные участники системы.
| Актор | Высокоуровневая цель | Боль / проблема сейчас | Критерий успеха |
|---|---|---|---|
| … | … | … | … |

### Функциональные требования (Functional Requirements)
Атомарные требования — одно действие системы на каждый пункт. Глагол в инфинитиве.
1. **FR-01 [Название]:** Система должна … [условие триггера] → [ожидаемый результат].
2. **FR-02 [Название]:** …

### Нефункциональные требования (Non-Functional Requirements)
Качественные характеристики с измеримыми SLA. Без абстракций.
| Категория | Требование | Метрика / SLA | Метод проверки |
|---|---|---|---|
| Производительность | … | Response time ≤ … ms при … RPS | Нагрузочный тест |
| Безопасность | … | … | Penetration test |
| Доступность | … | Uptime ≥ …% / RTO ≤ … мин | Мониторинг |
| UI/UX | … | … | Юзабилити-тест |
| Масштабируемость | … | … | … |

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
    """Strip ```mermaid ... ``` wrappers and normalise the diagram string."""
    raw = re.sub(r"```mermaid\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```\s*",        "", raw)
    raw = re.sub(r"\[TAB_\d\]\s*", "", raw)   # remove stray markers
    # Keep only lines that look like Mermaid syntax
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Skip pure markdown prose lines (start with #, *, -, |, _) — not Mermaid
        if re.match(r"^[#*_]", s) and not re.match(r"^(graph|flowchart|sequenceDiagram)", s):
            continue
        lines.append(ln)
    result = "\n".join(lines).strip()
    # Ensure it starts with a valid Mermaid diagram type
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
## Пирамида требований (BR / UR / FR / NFR)

### 🏢 Бизнес-требования (Business Requirements)
- **BR-01 [Скорость инвентаризации]:** Сократить время полной инвентаризации склада.
  - KPI As-Is (сейчас): 3 рабочих дня, 15% ошибок
  - KPI To-Be (цель): 4 часа, 0% ошибок
- **BR-02 [Себестоимость операций]:** Снизить операционные затраты на складские операции.
  - KPI As-Is: 120 000 ₽/мес на ручной учёт
  - KPI To-Be: ≤ 30 000 ₽/мес (автоматизация)
- **BR-03 [Клиентский сервис]:** Повысить точность и скорость отгрузки.
  - KPI As-Is: 92% точность, среднее время отгрузки 45 мин
  - KPI To-Be: 99.9% точность, ≤ 15 мин

### 👤 Пользовательские требования (User Requirements)
| Актор | Высокоуровневая цель | Боль / проблема сейчас |
|---|---|---|
| Кладовщик | Быстро принимать и отгружать товар без бумаг | Ручной ввод в Excel, постоянные ошибки |
| Менеджер склада | Видеть остатки и отчёты в реальном времени | Данные устаревают, нет единой картины |
| Директор | Контролировать KPI и видеть аналитику | Нет дашборда, данные собираются вручную |
| Бухгалтер | Получать корректные накладные автоматически | Ручная выписка накладных, ошибки в учёте |

### ⚙️ Функциональные требования (Functional Requirements)
1. **FR-01 [Авторизация по ролям]:** Система должна обеспечивать вход по логину/паролю с разграничением прав (кладовщик / менеджер / директор / бухгалтер).
2. **FR-02 [Приёмка с QR-кодом]:** Система должна позволять кладовщику сканировать QR-код и автоматически обновлять остатки при приёмке.
3. **FR-03 [Отгрузка и накладная]:** Система должна формировать электронную накладную при каждой отгрузке и уменьшать остаток в реальном времени.
4. **FR-04 [Остатки в реальном времени]:** Система должна отображать актуальные остатки по каждому SKU с задержкой не более 1 секунды.
5. **FR-05 [Автоуведомления]:** Система должна отправлять push-уведомление менеджеру при достижении минимального порога остатка.
6. **FR-06 [Отчёты и экспорт]:** Система должна предоставлять отчёты по движению товаров за произвольный период с экспортом в Excel и PDF.

### 🔒 Нефункциональные требования (Non-Functional Requirements)
| Категория | Требование | Метрика / SLA |
|---|---|---|
| Производительность | Загрузка любого экрана | ≤ 2 сек при 50 одновременных пользователях |
| Безопасность | Шифрование паролей | bcrypt, соль ≥ 12 раундов; HTTPS обязателен |
| Доступность | Время работы сервиса | Uptime ≥ 99.5% в рабочее время (08:00–22:00) |
| UI/UX | Освоение системы | Новый кладовщик без обучения за ≤ 30 минут |
| Масштабируемость | Рост нагрузки | Архитектура выдерживает x10 пользователей без рефакторинга |
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
    Start([🟢 Начало: Запрос приёмки]) --> Auth{Кладовщик\nавторизован?}
    Auth -->|Нет| Login[Экран входа]
    Login --> Auth
    Auth -->|Да| OpenForm[Открыть форму приёмки]
    OpenForm --> ScanQR[Сканировать QR накладной]
    ScanQR --> LoadItems[Загрузить список позиций]
    LoadItems --> ScanItem[Сканировать единицу товара]
    ScanItem --> SKUCheck{SKU найден\nв справочнике?}
    SKUCheck -->|Нет| CreateSKU[Создать позицию\nноменклатуры]
    CreateSKU --> ScanItem
    SKUCheck -->|Да| CountUp[Увеличить счётчик]
    CountUp --> MoreItems{Ещё позиции?}
    MoreItems -->|Да| ScanItem
    MoreItems -->|Нет| Compare[Сравнить факт\nс накладной]
    Compare --> Diff{Есть\nрасхождения?}
    Diff -->|Да| ActDiff[Создать акт расхождения\nУведомить менеджера]
    ActDiff --> Sign[Подписать приёмку]
    Diff -->|Нет| Sign
    Sign --> UpdateStock[Обновить остатки]
    UpdateStock --> DBCheck{Запись\nв БД успешна?}
    DBCheck -->|Нет| Buffer[Сохранить в буфер\noffline mode]
    Buffer --> Retry[Повторить при\nвосстановлении связи]
    Retry --> UpdateStock
    DBCheck -->|Да| CreateDoc[Создать приходную\nнакладную]
    CreateDoc --> Notify[Уведомить бухгалтера]
    Notify --> End([🔴 Конец: Приёмка завершена])\
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
