import os
import re
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd

app = FastAPI(title="BAlance.ai — Business Process Documentation Generator")
_HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")

# ---------------------------------------------------------------------------
# AI client
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI as _OpenAI
    _OPENAI_LIB = True
except Exception:
    _OPENAI_LIB = False


def get_ai_client():
    if not _OPENAI_LIB:
        return None, None
    try:
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            return _OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key), "llama-3.1-8b-instant"
    except Exception:
        pass
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            return _OpenAI(api_key=openai_key), "gpt-4o"
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# UNIVERSAL DATA ANALYSIS — works with any tabular data
# ---------------------------------------------------------------------------
def analyze_dataframe(df: pd.DataFrame) -> dict:
    result = {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "column_names": list(df.columns),
        "context_str": "",
        "insights": [],
    }

    col_summaries = []
    for col in df.columns[:15]:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        fill_pct = round(non_null / len(df) * 100, 0) if len(df) > 0 else 0
        if df[col].dtype == object:
            n_unique = df[col].nunique()
            top_vals = df[col].dropna().value_counts().head(3).index.tolist()
            top_str = ", ".join(str(v) for v in top_vals)
            col_summaries.append(
                f"'{col}' (текст, {n_unique} уник., заполн. {fill_pct}%, топ: {top_str})"
            )
            if n_unique <= 20 and n_unique > 1:
                result["insights"].append(f"Колонка «{col}»: категории — {top_str}")
        else:
            try:
                mean_val = round(df[col].mean(), 2)
                max_val = df[col].max()
                col_summaries.append(
                    f"'{col}' (число, среднее={mean_val}, макс={max_val}, заполн. {fill_pct}%)"
                )
                result["insights"].append(f"«{col}»: среднее {mean_val} (макс: {max_val})")
            except Exception:
                col_summaries.append(f"'{col}' (тип: {dtype}, заполн. {fill_pct}%)")

    result["context_str"] = (
        f"Таблица бизнес-процесса: {len(df)} строк, {len(df.columns)} колонок. "
        f"Структура: {'; '.join(col_summaries[:10])}."
    )
    return result


# ---------------------------------------------------------------------------
# MERMAID CLEANING
# ---------------------------------------------------------------------------
def _clean_mermaid(code: str) -> str:
    code = re.sub(r"```mermaid\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"```\s*", "", code)
    code = code.strip()
    # Ensure it starts with a valid graph declaration
    if code and not re.match(r"^\s*(graph|flowchart|sequenceDiagram|classDiagram)", code):
        code = "graph TD\n" + code
    return code


# ---------------------------------------------------------------------------
# DEMO MERMAID CONTENT
# ---------------------------------------------------------------------------
DEMO_MERMAID_ASIS = """graph TD
    A([🚀 Старт: Входящий лид]) --> B{Ручная квалификация менеджером}
    B -->|Целевой клиент| C[Назначение менеджера вручную]
    B -->|Нецелевой| Z1([❌ Потеря лида])
    C --> D[Первый звонок по телефону]
    D -->|Дозвонились| E[КП в Excel — ручная работа]
    D -->|Не дозвонились| F[Повторная попытка через 3 дня]
    F --> G{Третья попытка?}
    G -->|Да| D
    G -->|Нет| Z2([❌ Потеря: недозвон])
    E --> H[Согласование КП с руководителем]
    H -->|Согласовано| I[Отправка КП клиенту по email]
    H -->|Отказано| J[Доработка КП]
    J --> H
    I --> K{Ответ клиента}
    K -->|Интерес| L[Переговоры — несколько встреч]
    K -->|Игнор 7 дней| M[Ручной follow-up]
    M --> K
    K -->|Отказ| Z3([❌ Lost: Цена или конкурент])
    L --> N[Подготовка договора юристом]
    N --> O{Согласование юристом}
    O -->|Замечания| P[Правки договора]
    P --> O
    O --> Q[Подписание договора вручную]
    Q --> R[Выставление счёта вручную в 1С]
    R --> S{Оплата поступила?}
    S -->|Оплачено| T([✅ Сделка: Won])
    S -->|Просрочка 3 дня| U[Ручное напоминание об оплате]
    U --> S
    S -->|Просрочка 30 дней| Z4([❌ Потеря: неплатёж])"""

DEMO_MERMAID_TOBE = """graph TD
    A([⚡ Триггер: Лид из любого канала]) --> B[Авто-обогащение: компания, должность, сайт]
    B --> C{AI-скоринг по ICP}
    C -->|Score ≥ 70 — горячий| D[Авто-назначение менеджеру по алгоритму загруженности]
    C -->|Score 40–69 — тёплый| E[Нуртеринг: авто-серия писем CRM]
    C -->|Score < 40 — холодный| F[Авто-архивация + ремаркетинг]
    D --> G[Авто-уведомление менеджеру в Slack + задача в CRM]
    G --> H{Контакт ≤ 2ч по SLA?}
    H -->|Нет| I[Авто-эскалация руководителю]
    H -->|Да| J[Звонок + авто-транскрипция AI]
    I --> J
    J --> K[Авто-генерация КП из шаблона CRM]
    K --> L[Авто-отправка + трекинг открытий]
    L --> M{КП открыто?}
    M -->|Нет, 48ч| N[Авто-follow-up SMS + email]
    M -->|Да| O[Авто-уведомление менеджеру: клиент читает]
    N --> M
    O --> P[Онлайн-встреча: Calendly-интеграция]
    P --> Q[Авто-генерация договора из шаблона]
    Q --> R[E-sign: DocuSign / Контур.Подпись]
    R --> S[Авто-счёт: интеграция с 1С / Сбер Бизнес]
    S --> T{Предиктивный риск-анализ оплаты}
    T -->|Риск высокий| U[Авто-алерт: руководитель + финансист]
    T -->|Риск низкий| V[Авто-мониторинг: банк-интеграция]
    U --> W[Персональное общение + оффер]
    W --> V
    V --> X([✅ Won: авто-закрытие + аналитика в дашборде])"""

DEMO_SPEC = """# Спецификация требований — Демо-режим

**Дата:** {date} | **Статус:** Демо | **Источник:** BAlance.ai

---

## 1. Бизнес-требования (Business Requirements)

**Цель:** Сократить время обработки сделки на 60% и устранить ручные операции в ключевых точках процесса.

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время от лида до КП | 3–5 дней | < 2 часов |
| Доля ручного труда | ~80% | < 15% |
| Конверсия лид→сделка | 12% | > 25% |
| SLA первого контакта | нет контроля | ≤ 2 часов |

---

## 2. Пользовательские требования (User Requirements)

**UC-01: Автоматизация обработки входящего лида**

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | Система | Получает лид из любого канала | Лид создан в CRM |
| 2 | AI-модуль | Скоринг и обогащение данных | Приоритет установлен |
| 3 | Система | Назначает менеджера по алгоритму | Задача поставлена |
| 4 | Менеджер | Первый контакт ≤ 2ч | Встреча запланирована |
| 5 | Система | Генерирует КП из шаблона | КП отправлено + трекинг |

- **Предусловия:** Лид зарегистрирован в системе
- **Расширения:** При нарушении SLA — авто-эскалация руководителю
- **Постусловия:** Сделка переведена в следующую стадию

---

## 3. Функциональные требования (Functional Requirements)

- **FR-01** Авто-скоринг входящих лидов по модели ICP (Ideal Customer Profile)
- **FR-02** Авто-назначение менеджера с учётом загруженности и специализации
- **FR-03** SLA-контроль первого контакта с эскалацией при нарушении
- **FR-04** Авто-генерация КП из шаблонов CRM с трекингом открытий
- **FR-05** Авто-генерация договора + E-sign интеграция
- **FR-06** Авто-выставление счёта через интеграцию с 1С / банком
- **FR-07** Предиктивный анализ риска срыва сделки
- **FR-08** Дашборд воронки с конверсией по каждому этапу в реальном времени

---

## 4. Нефункциональные требования (Non-Functional Requirements)

- **NFR-01 Производительность:** Скоринг лида ≤ 5 сек, генерация КП ≤ 30 сек
- **NFR-02 Безопасность:** Шифрование данных AES-256, авторизация OAuth 2.0, журнал аудита
- **NFR-03 Доступность:** SLA ≥ 99.5% uptime, RTO ≤ 1 час
- **NFR-04 Масштабируемость:** Поддержка до 10 000 лидов/месяц без деградации
- **NFR-05 Интерфейс:** Мобильная версия, время отклика UI < 200 мс, WCAG 2.1 AA
"""

DEMO_RTM = """# Матрица трассировки требований (RTM)

| ID | Тип | Описание фичи | Приоритет |
|----|-----|---------------|-----------|
| BR-01 | Бизнес | Сократить время лид→КП до 2 часов | Must |
| BR-02 | Бизнес | Повысить конверсию лид→сделка до 25% | Must |
| BR-03 | Бизнес | Устранить ручной ввод данных на 85% | Must |
| BR-04 | Бизнес | SLA первого контакта ≤ 2 часов | Should |
| UR-01 | Пользователь | AI-скоринг и квалификация лидов | Must |
| UR-02 | Пользователь | Авто-назначение менеджеров | Must |
| UR-03 | Пользователь | Авто-генерация КП из шаблона | Must |
| UR-04 | Пользователь | Трекинг открытия КП | Should |
| UR-05 | Пользователь | E-sign интеграция (DocuSign/Контур) | Should |
| FR-01 | Функциональное | Модуль скоринга ICP | Must |
| FR-02 | Функциональное | Алгоритм распределения лидов | Must |
| FR-03 | Функциональное | Авто-генерация КП + договора | Must |
| FR-04 | Функциональное | Интеграция с 1С / банком | Should |
| FR-05 | Функциональное | Предиктивная аналитика риска | Could |
| FR-06 | Функциональное | Дашборд конверсии в реальном времени | Should |
| NFR-01 | Нефункциональное | SLA скоринга ≤ 5 сек | Must |
| NFR-02 | Нефункциональное | Шифрование AES-256 + OAuth 2.0 | Must |
| NFR-03 | Нефункциональное | Доступность ≥ 99.5% uptime | Must |
| NFR-04 | Нефункциональное | Масштаб: 10 000 лидов/месяц | Should |
| NFR-05 | Нефункциональное | Мобильная версия + WCAG 2.1 AA | Could |
"""

# ---------------------------------------------------------------------------
# System prompt — Mermaid-based output
# ---------------------------------------------------------------------------
_SYSTEM = """Ты — Senior Business Analyst и Solution Architect. Анализируешь структуру любой бизнес-таблицы и генерируешь полную проектную документацию.

Ответ строго в следующем формате — ЧЕТЫРЕ раздела, каждый начинается с маркера НА ОТДЕЛЬНОЙ строке:

MERMAID_ASIS:
[код Mermaid для As-Is диаграммы]
MERMAID_TOBE:
[код Mermaid для To-Be диаграммы]
SPEC:
[полная спецификация требований в Markdown]
RTM:
[матрица трассировки в Markdown]

===== ПРАВИЛА ДЛЯ MERMAID_ASIS =====
- Синтаксис: graph TD (сверху вниз)
- Минимум 15–20 узлов и развилок
- Отображает ТЕКУЩИЙ ручной/хаотичный процесс на основе колонок файла
- Показывай: ручные операции, ветвления на отказах, зависания, потери конверсии, многократные согласования
- Узлы: круглые скобки (([...])) для начала/конца, фигурные {} для решений, квадратные [] для задач
- НЕ используй кавычки внутри квадратных скобок узлов, пиши текст без спецсимволов
- Стрелки только через --> или -->|подпись|

===== ПРАВИЛА ДЛЯ MERMAID_TOBE =====
- Синтаксис: graph TD (сверху вниз)
- Минимум 15–20 узлов и развилок
- Отображает ЦЕЛЕВОЙ автоматизированный процесс
- Показывай: авто-триггеры, AI-модули, системные интеграции, SLA-контроль, эскалации, предиктивную аналитику
- Те же правила синтаксиса что для ASIS
- Узлы и подписи строго на русском языке

===== ПРАВИЛА ДЛЯ SPEC =====
Markdown-документ строго по 4 уровням:

# Спецификация требований

## 1. Бизнес-требования (Business Requirements)
[Цель, бизнес-эффект, таблица метрик As-Is vs To-Be с конкретными цифрами из данных файла]

## 2. Пользовательские требования (User Requirements)
[UC по Коберну: таблица Шаг/Актор/Действие/Результат, предусловия, расширения, постусловия]

## 3. Функциональные требования (Functional Requirements)
[Список FR-XX: что конкретно делает система — валидация, интеграции, авто-уведомления, хранение]

## 4. Нефункциональные требования (Non-Functional Requirements)
[NFR-XX: Производительность, Безопасность, Доступность, Масштабируемость — с конкретными метриками]

===== ПРАВИЛА ДЛЯ RTM =====
Строго Markdown-таблица, минимум 18 строк:

# Матрица трассировки требований (RTM)

| ID | Тип | Описание фичи | Приоритет |
|----|-----|---------------|-----------|
[Строки с типами: Бизнес, Пользователь, Функциональное, Нефункциональное; приоритеты: Must / Should / Could]

ВАЖНО: Никаких пояснений вне четырёх разделов. Маркеры MERMAID_ASIS:, MERMAID_TOBE:, SPEC:, RTM: — строго на отдельных строках. Для Mermaid НЕ оборачивай код в ```mermaid ``` — только чистый синтаксис."""


def _build_prompt(context_str: str, user_problem: str, insights: list) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    insight_str = " ".join(insights[:5]) if insights else ""
    problem_part = f" Задача: {user_problem.strip()}." if user_problem.strip() else ""
    return (
        f"Сегодня: {today}. {context_str}{problem_part} Наблюдения: {insight_str}"
    ).strip()


def _parse_ai_response(text: str) -> dict:
    def extract_block(start_marker, end_markers, text):
        pattern = rf"^{re.escape(start_marker)}\s*\n([\s\S]+?)(?=\n(?:{'|'.join(re.escape(m) for m in end_markers)})|\Z)"
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    all_markers = ["MERMAID_ASIS:", "MERMAID_TOBE:", "SPEC:", "RTM:"]
    mermaid_asis = extract_block("MERMAID_ASIS:", ["MERMAID_TOBE:", "SPEC:", "RTM:"], text)
    mermaid_tobe = extract_block("MERMAID_TOBE:", ["SPEC:", "RTM:"], text)
    spec_text    = extract_block("SPEC:",          ["RTM:"], text)
    rtm_text     = extract_block("RTM:",           [], text)

    return {
        "mermaid_asis": _clean_mermaid(mermaid_asis),
        "mermaid_tobe": _clean_mermaid(mermaid_tobe),
        "spec":         spec_text or "",
        "rtm":          rtm_text or "",
    }


def _call_ai(context_str: str, user_problem: str, insights: list) -> dict:
    client, model = get_ai_client()
    if client is None:
        return None
    prompt = _build_prompt(context_str, user_problem, insights)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.35,
        max_tokens=4000,
    )
    return _parse_ai_response(str(resp.choices[0].message.content))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(_HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/analyze")
async def analyze(
    problem: str = Form(default=""),
    file: UploadFile = File(default=None),
):
    df = None
    if file and file.filename:
        fname = file.filename.lower()
        if fname.endswith((".xlsx", ".xls")):
            try:
                file.file.seek(0)
                df = pd.read_excel(file.file, engine="openpyxl")
            except Exception as e:
                return JSONResponse({"error": f"Ошибка чтения Excel: {e}"}, status_code=400)
        elif fname.endswith(".csv"):
            try:
                file.file.seek(0)
                df = pd.read_csv(file.file)
            except Exception as e:
                return JSONResponse({"error": f"Ошибка чтения CSV: {e}"}, status_code=400)
        else:
            return JSONResponse(
                {"error": "Поддерживаются только .csv, .xls, .xlsx."},
                status_code=400,
            )

    if df is None and not problem.strip():
        return JSONResponse(
            {"error": "Загрузите файл или введите описание бизнес-процесса."},
            status_code=400,
        )

    analysis   = {}
    file_stats = None
    if df is not None:
        analysis = analyze_dataframe(df)
        file_stats = {
            "rows":     analysis["total_rows"],
            "columns":  analysis["column_names"],
            "insights": analysis["insights"],
        }

    context_str = analysis.get("context_str", "")
    insights    = analysis.get("insights", [])

    client, _  = get_ai_client()
    is_demo    = client is None
    demo_reason = None

    if is_demo:
        ai = None
        demo_reason = "GROQ_API_KEY не задан — активирован демо-режим"
    else:
        try:
            ai = _call_ai(context_str, problem, insights)
            if not ai or not ai.get("mermaid_asis"):
                ai = None
                is_demo = True
                demo_reason = "AI вернул пустой ответ — показан шаблон"
        except Exception as e:
            ai = None
            is_demo = True
            demo_reason = f"Ошибка AI: {e}"

    today = datetime.now().strftime("%d.%m.%Y")
    if ai:
        mermaid_asis = ai["mermaid_asis"]
        mermaid_tobe = ai["mermaid_tobe"]
        spec         = ai["spec"]
        rtm          = ai["rtm"]
    else:
        mermaid_asis = DEMO_MERMAID_ASIS
        mermaid_tobe = DEMO_MERMAID_TOBE
        spec         = DEMO_SPEC.format(date=today)
        rtm          = DEMO_RTM

    return JSONResponse({
        "mermaid_asis": mermaid_asis,
        "mermaid_tobe": mermaid_tobe,
        "spec":         spec,
        "rtm":          rtm,
        "demo":         is_demo,
        "demo_reason":  demo_reason,
        "file_stats":   file_stats,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
