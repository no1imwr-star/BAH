import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd

app = FastAPI(title="BAlance.ai — BPMN to Requirements Documentation Generator")
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
# BPMN XML PARSER
# ---------------------------------------------------------------------------
# Task element local-names we care about
_TASK_TAGS = {
    "task", "usertask", "servicetask", "scripttask", "manualtask",
    "businessruletask", "sendtask", "receivetask", "calledactivity",
    "subprocess",
}
_ACTOR_TAGS = {"participant", "lane"}
_PROCESS_TAGS = {"process", "collaboration"}


def _local(tag: str) -> str:
    """Return the local name of an ElementTree tag (strips namespace URI)."""
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()


def _attr_name(el) -> str:
    return (el.get("name") or "").strip()


def parse_bpmn(content: bytes) -> dict:
    """
    Parse BPMN 2.0 XML and extract:
      - tasks: list of task/step names
      - actors: list of participant/lane names
      - process_name: top-level process name
      - raw_steps_text: comma-joined task names for prompting
    Falls back to regex extraction if XML parse fails.
    """
    tasks, actors, process_name = [], [], ""

    try:
        root = ET.fromstring(content)

        # Collect all elements by local tag
        for el in root.iter():
            local = _local(el.tag)
            name  = _attr_name(el)

            if local in _TASK_TAGS and name:
                tasks.append(name)
            elif local in _ACTOR_TAGS and name:
                actors.append(name)
            elif local == "process" and name and not process_name:
                process_name = name
            elif local == "collaboration" and name and not process_name:
                process_name = name

        # Deduplicate while preserving order
        tasks  = list(dict.fromkeys(tasks))
        actors = list(dict.fromkeys(actors))

    except ET.ParseError:
        # Fallback: regex extraction for malformed XML
        text = content.decode("utf-8", errors="replace")
        tasks  = re.findall(r'<(?:bpmn:)?(?:userTask|serviceTask|task|manualTask)[^>]+name="([^"]+)"', text)
        actors = re.findall(r'<(?:bpmn:)?(?:participant|lane)[^>]+name="([^"]+)"', text)
        m = re.search(r'<(?:bpmn:)?process[^>]+name="([^"]+)"', text)
        process_name = m.group(1) if m else ""

    return {
        "tasks":           tasks,
        "actors":          actors,
        "process_name":    process_name,
        "task_count":      len(tasks),
        "actor_count":     len(actors),
        "context_str":     _build_bpmn_context(tasks, actors, process_name),
    }


def _build_bpmn_context(tasks: list, actors: list, process_name: str) -> str:
    parts = []
    if process_name:
        parts.append(f"Название процесса: «{process_name}».")
    if actors:
        parts.append(f"Участники/роли: {', '.join(actors[:10])}.")
    if tasks:
        numbered = "; ".join(f"{i+1}. {t}" for i, t in enumerate(tasks[:25]))
        parts.append(f"Шаги процесса ({len(tasks)} шт.): {numbered}.")
    if not parts:
        parts.append("BPMN-файл не содержит именованных шагов.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------
_SYSTEM = """Ты — Senior Business Analyst и System Analyst с опытом в BPMN, разработке требований и управлении бэклогом. Тебе предоставлена структура бизнес-процесса, извлечённая из BPMN-файла.

Твоя задача — декомпозировать этот визуальный процесс в текстовую проектную документацию на русском языке.

Ответ строго в следующем формате — ТРИ раздела, каждый начинается с маркера НА ОТДЕЛЬНОЙ строке:

---SECTION1---
[содержимое]
---SECTION2---
[содержимое]
---SECTION3---
[содержимое]

===== РАЗДЕЛ 1: ПОЛНАЯ СПЕЦИФИКАЦИЯ ТРЕБОВАНИЙ =====
Markdown-документ по четырём уровням:

# Спецификация требований

## 1.1 Бизнес-требования (Business Requirements)
- Бизнес-цели автоматизации данного процесса
- Таблица: Метрика | As-Is (текущее) | To-Be (целевое) — с конкретными цифрами

## 1.2 Пользовательские требования (User Requirements)
- Use Case по Коберну на основе шагов BPMN
- Таблица: Шаг | Актор | Действие | Результат
- Предусловия, расширения, постусловия

## 1.3 Функциональные требования (Functional Requirements)
- FR-XX для каждого шага BPMN: валидации, интеграции, триггеры, уведомления

## 1.4 Нефункциональные требования (Non-Functional Requirements)
- NFR-XX: Производительность, Безопасность, Доступность, Интерфейс — с метриками

===== РАЗДЕЛ 2: МАТРИЦА ТРАССИРОВКИ И ПРИОРИТИЗАЦИИ (MoSCoW RTM) =====
Markdown-таблица, минимум 15 строк, привязанная к шагам исходного BPMN:

# Матрица трассировки требований (RTM)

| ID | Тип | Описание функциональной фичи | Связь с шагом BPMN | Приоритет |
|----|-----|------------------------------|---------------------|-----------|
[Must / Should / Could]

===== РАЗДЕЛ 3: БЭКЛОГ ДЛЯ JIRA (User Stories) =====
Готовые User Stories для разработчиков — по одной истории на каждый ключевой шаг BPMN:

# Бэклог проекта — User Stories

## US-XX: [Краткое название]
**Роль:** [Актор из BPMN]
**История:** Как [Роль], я хочу [Функционал], чтобы [Бизнес-ценность].

**Критерии приёмки (Acceptance Criteria):**
- [ ] AC-1: ...
- [ ] AC-2: ...
- [ ] AC-3: ...

---

ВАЖНО: Никаких пояснений вне трёх разделов. Маркеры ---SECTION1---, ---SECTION2---, ---SECTION3--- строго на отдельных строках. Всё содержимое строго на русском языке."""


def _parse_ai_response(text: str) -> dict:
    def extract_section(n, text):
        start = f"---SECTION{n}---"
        end   = f"---SECTION{n+1}---"
        idx_s = text.find(start)
        if idx_s == -1:
            return ""
        idx_s += len(start)
        idx_e = text.find(end, idx_s)
        chunk = text[idx_s: idx_e if idx_e != -1 else None]
        return chunk.strip()

    return {
        "spec":    extract_section(1, text),
        "rtm":     extract_section(2, text),
        "backlog": extract_section(3, text),
    }


def _call_ai(bpmn_context: str, user_goals: str) -> dict:
    client, model = get_ai_client()
    if client is None:
        return None
    today = datetime.now().strftime("%d.%m.%Y")
    user_msg = f"Сегодня: {today}.\n\n{bpmn_context}"
    if user_goals.strip():
        user_msg += f"\n\nДополнительные бизнес-цели: {user_goals.strip()}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=4000,
    )
    return _parse_ai_response(str(resp.choices[0].message.content))


# ---------------------------------------------------------------------------
# DEMO CONTENT
# ---------------------------------------------------------------------------
DEMO_SPEC = """# Спецификация требований — Демо-режим

**Дата:** {date} | **Статус:** Демо | **Источник:** BAlance.ai

---

## 1.1 Бизнес-требования (Business Requirements)

**Цель:** Автоматизировать процесс согласования заявок и устранить ручной контроль на каждом шаге.

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время согласования | 5–7 рабочих дней | < 4 часов |
| Доля ручных операций | ~75% | < 10% |
| Ошибки при передаче данных | ~12% | < 1% |
| SLA первичной обработки | нет контроля | ≤ 2 часов |

---

## 1.2 Пользовательские требования (User Requirements)

**UC-01: Подача и согласование заявки**

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | Инициатор | Создаёт заявку в системе | Заявка зарегистрирована |
| 2 | Система | Авто-валидация полей | Заявка направлена на согласование |
| 3 | Руководитель | Рассматривает и согласует | Статус изменён |
| 4 | Система | Отправляет уведомление | Инициатор получает результат |

- **Предусловия:** Пользователь авторизован, шаблон заявки настроен
- **Расширения:** Если согласующий недоступен > 24ч — авто-эскалация
- **Постусловия:** Заявка в финальном статусе, аудит-лог сохранён

---

## 1.3 Функциональные требования (Functional Requirements)

- **FR-01** Форма создания заявки с обязательными и необязательными полями
- **FR-02** Авто-валидация заполненности и форматов при отправке
- **FR-03** Маршрутизация заявки согласно матрице согласований
- **FR-04** Уведомления по email/push при смене статуса
- **FR-05** SLA-таймер с авто-эскалацией при нарушении срока
- **FR-06** Полный аудит-лог всех действий по заявке

---

## 1.4 Нефункциональные требования (Non-Functional Requirements)

- **NFR-01 Производительность:** Обработка заявки ≤ 3 сек при 500 req/min
- **NFR-02 Безопасность:** Шифрование AES-256, RBAC, журнал доступа
- **NFR-03 Доступность:** SLA ≥ 99.5%, RTO ≤ 1 час
- **NFR-04 Интерфейс:** Адаптивный дизайн, время отклика UI < 200 мс
"""

DEMO_RTM = """# Матрица трассировки требований (RTM)

| ID | Тип | Описание функциональной фичи | Связь с шагом BPMN | Приоритет |
|----|-----|------------------------------|--------------------|-----------|
| BR-01 | Бизнес | Сократить время согласования до 4 ч | Весь процесс | Must |
| BR-02 | Бизнес | Устранить ручной ввод данных на 75% | Шаг 1–2 | Must |
| BR-03 | Бизнес | SLA первичной обработки ≤ 2 ч | Шаг 2 | Must |
| UR-01 | Пользователь | Форма создания заявки с валидацией | Шаг 1 | Must |
| UR-02 | Пользователь | Авто-уведомления при смене статуса | Шаг 4 | Must |
| UR-03 | Пользователь | Просмотр истории согласований | Шаг 3–4 | Should |
| FR-01 | Функциональное | Авто-валидация полей формы | Шаг 2 | Must |
| FR-02 | Функциональное | Маршрутизация по матрице согласований | Шаг 3 | Must |
| FR-03 | Функциональное | SLA-таймер с авто-эскалацией | Шаг 3 | Must |
| FR-04 | Функциональное | Email/Push уведомления | Шаг 4 | Should |
| FR-05 | Функциональное | Аудит-лог всех действий | Все шаги | Should |
| NFR-01 | Нефункциональное | Производительность ≤ 3 сек | Все шаги | Must |
| NFR-02 | Нефункциональное | RBAC + шифрование AES-256 | Все шаги | Must |
| NFR-03 | Нефункциональное | SLA ≥ 99.5% uptime | Вся система | Must |
| NFR-04 | Нефункциональное | Адаптивный UI | Шаг 1, 4 | Could |
"""

DEMO_BACKLOG = """# Бэклог проекта — User Stories

## US-01: Создание заявки
**Роль:** Инициатор
**История:** Как Инициатор, я хочу создать заявку через веб-форму, чтобы запустить процесс согласования без участия администратора.

**Критерии приёмки (Acceptance Criteria):**
- [ ] AC-1: Форма доступна после авторизации и содержит все обязательные поля
- [ ] AC-2: При отправке незаполненных обязательных полей отображается ошибка
- [ ] AC-3: Успешно созданная заявка получает уникальный номер и статус «Новая»

---

## US-02: Авто-валидация данных
**Роль:** Система
**История:** Как Система, я хочу автоматически проверять корректность данных заявки, чтобы исключить ошибки до начала согласования.

**Критерии приёмки (Acceptance Criteria):**
- [ ] AC-1: Проверяются форматы всех полей (дата, сумма, email)
- [ ] AC-2: При ошибке пользователь видит конкретное сообщение с указанием поля
- [ ] AC-3: Валидная заявка немедленно направляется согласующему

---

## US-03: Согласование заявки
**Роль:** Руководитель
**История:** Как Руководитель, я хочу получать уведомления о новых заявках и согласовывать их в один клик, чтобы не тратить время на поиск документов.

**Критерии приёмки (Acceptance Criteria):**
- [ ] AC-1: Уведомление приходит в течение 5 минут после поступления заявки
- [ ] AC-2: Из уведомления можно перейти к заявке и принять решение без дополнительной авторизации
- [ ] AC-3: При нарушении SLA (> 24ч) система автоматически эскалирует заявку

---

## US-04: Уведомление об итоге
**Роль:** Инициатор
**История:** Как Инициатор, я хочу получать уведомление о результате согласования, чтобы своевременно принять следующие шаги.

**Критерии приёмки (Acceptance Criteria):**
- [ ] AC-1: Уведомление приходит в течение 2 минут после принятия решения
- [ ] AC-2: В уведомлении указан результат, комментарий и ссылка на заявку
- [ ] AC-3: История уведомлений доступна в личном кабинете
"""

DEMO_STATS = {"task_count": 4, "actor_count": 2, "process_name": "Согласование заявок (демо)"}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(_HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/analyze")
async def analyze(
    goals: str = Form(default=""),
    file: UploadFile = File(default=None),
):
    bpmn_data    = None
    parse_error  = None

    if file and file.filename:
        fname = (file.filename or "").lower()
        if not fname.endswith(".bpmn"):
            return JSONResponse(
                {"error": "Поддерживается только формат .bpmn. Загрузите BPMN 2.0-файл."},
                status_code=400,
            )
        try:
            file.file.seek(0)
            content = file.file.read()
            bpmn_data = parse_bpmn(content)
            if bpmn_data["task_count"] == 0:
                parse_error = "В файле не найдено именованных шагов. Убедитесь, что задачи в BPMN имеют атрибут name."
        except Exception as e:
            return JSONResponse({"error": f"Ошибка чтения BPMN: {e}"}, status_code=400)
    else:
        if not goals.strip():
            return JSONResponse(
                {"error": "Загрузите .bpmn-файл или введите описание бизнес-процесса в поле целей."},
                status_code=400,
            )
        # Text-only mode: construct a minimal context from the goals text
        bpmn_data = {
            "tasks":        [],
            "actors":       [],
            "process_name": "",
            "task_count":   0,
            "actor_count":  0,
            "context_str":  f"Описание процесса от пользователя: {goals.strip()}",
        }

    client, _  = get_ai_client()
    is_demo    = client is None
    demo_reason = None

    if is_demo:
        ai = None
        demo_reason = "GROQ_API_KEY не задан — показан демо-шаблон"
    else:
        try:
            ai = _call_ai(bpmn_data["context_str"], goals)
            if not ai or not ai.get("spec"):
                ai = None
                is_demo = True
                demo_reason = "AI вернул пустой ответ — показан демо-шаблон"
        except Exception as e:
            ai = None
            is_demo = True
            demo_reason = f"Ошибка AI: {e}"

    today = datetime.now().strftime("%d.%m.%Y")
    if ai:
        spec    = ai["spec"]
        rtm     = ai["rtm"]
        backlog = ai["backlog"]
    else:
        spec    = DEMO_SPEC.format(date=today)
        rtm     = DEMO_RTM
        backlog = DEMO_BACKLOG

    stats = {
        "task_count":   bpmn_data["task_count"],
        "actor_count":  bpmn_data["actor_count"],
        "process_name": bpmn_data["process_name"],
        "tasks":        bpmn_data["tasks"][:10],
        "actors":       bpmn_data["actors"][:6],
        "parse_error":  parse_error,
    } if bpmn_data["task_count"] > 0 else None

    full_md = f"# BAlance.ai — Проектная документация\n\n**Дата:** {today}\n\n---\n\n{spec}\n\n---\n\n{rtm}\n\n---\n\n{backlog}"

    return JSONResponse({
        "spec":         spec,
        "rtm":          rtm,
        "backlog":      backlog,
        "full_md":      full_md,
        "demo":         is_demo,
        "demo_reason":  demo_reason,
        "stats":        stats,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
