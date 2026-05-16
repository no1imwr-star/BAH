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
                f"'{col}' (текст, {n_unique} уник. знач., заполн. {fill_pct}%, топ: {top_str})"
            )
            if n_unique <= 20 and n_unique > 1:
                result["insights"].append(f"Колонка «{col}»: {n_unique} категорий — {top_str}")
        else:
            try:
                mean_val = round(df[col].mean(), 2)
                max_val = df[col].max()
                col_summaries.append(
                    f"'{col}' (число, среднее={mean_val}, макс={max_val}, заполн. {fill_pct}%)"
                )
                if mean_val > 0:
                    result["insights"].append(f"Среднее «{col}»: {mean_val} (макс: {max_val})")
            except Exception:
                col_summaries.append(f"'{col}' (тип: {dtype}, заполн. {fill_pct}%)")

    result["context_str"] = (
        f"Таблица бизнес-процесса: {len(df)} строк, {len(df.columns)} колонок. "
        f"Структура: {'; '.join(col_summaries[:8])}."
    )
    return result


# ---------------------------------------------------------------------------
# BPMN TEMPLATES
# ---------------------------------------------------------------------------
def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def build_asis_bpmn(steps: list) -> str:
    s = [_esc(str(step).strip()[:40]) for step in (steps + [""] * 5)][:5]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn" id="Def_AsIs">
  <collaboration id="Collab_AsIs">
    <participant id="Pool_AsIs" name="As-Is: Текущий процесс" processRef="Proc_AsIs"/>
  </collaboration>
  <process id="Proc_AsIs" isExecutable="false">
    <startEvent id="AS_SE" name="Старт"><outgoing>AS_F1</outgoing></startEvent>
    <userTask   id="AS_T1" name="{s[0]}"><incoming>AS_F1</incoming><outgoing>AS_F2</outgoing></userTask>
    <userTask   id="AS_T2" name="{s[1]}"><incoming>AS_F2</incoming><outgoing>AS_F3</outgoing></userTask>
    <userTask   id="AS_T3" name="{s[2]}"><incoming>AS_F3</incoming><outgoing>AS_F4</outgoing></userTask>
    <userTask   id="AS_T4" name="{s[3]}"><incoming>AS_F4</incoming><outgoing>AS_F5</outgoing></userTask>
    <userTask   id="AS_T5" name="{s[4]}"><incoming>AS_F5</incoming><outgoing>AS_F6</outgoing></userTask>
    <endEvent   id="AS_EE" name="Завершено"><incoming>AS_F6</incoming></endEvent>
    <sequenceFlow id="AS_F1" sourceRef="AS_SE" targetRef="AS_T1"/>
    <sequenceFlow id="AS_F2" sourceRef="AS_T1" targetRef="AS_T2"/>
    <sequenceFlow id="AS_F3" sourceRef="AS_T2" targetRef="AS_T3"/>
    <sequenceFlow id="AS_F4" sourceRef="AS_T3" targetRef="AS_T4"/>
    <sequenceFlow id="AS_F5" sourceRef="AS_T4" targetRef="AS_T5"/>
    <sequenceFlow id="AS_F6" sourceRef="AS_T5" targetRef="AS_EE"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiag_AsIs">
    <bpmndi:BPMNPlane id="BPMNPlane_AsIs" bpmnElement="Collab_AsIs">
      <bpmndi:BPMNShape id="Pool_AsIs_di" bpmnElement="Pool_AsIs" isHorizontal="true">
        <dc:Bounds x="100" y="80" width="1120" height="180"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_SE_di" bpmnElement="AS_SE"><dc:Bounds x="152" y="161" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_T1_di" bpmnElement="AS_T1"><dc:Bounds x="238" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_T2_di" bpmnElement="AS_T2"><dc:Bounds x="388" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_T3_di" bpmnElement="AS_T3"><dc:Bounds x="538" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_T4_di" bpmnElement="AS_T4"><dc:Bounds x="688" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_T5_di" bpmnElement="AS_T5"><dc:Bounds x="838" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="AS_EE_di" bpmnElement="AS_EE"><dc:Bounds x="990" y="161" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="AS_F1_di" bpmnElement="AS_F1"><di:waypoint x="188" y="179"/><di:waypoint x="238" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="AS_F2_di" bpmnElement="AS_F2"><di:waypoint x="338" y="179"/><di:waypoint x="388" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="AS_F3_di" bpmnElement="AS_F3"><di:waypoint x="488" y="179"/><di:waypoint x="538" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="AS_F4_di" bpmnElement="AS_F4"><di:waypoint x="638" y="179"/><di:waypoint x="688" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="AS_F5_di" bpmnElement="AS_F5"><di:waypoint x="788" y="179"/><di:waypoint x="838" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="AS_F6_di" bpmnElement="AS_F6"><di:waypoint x="938" y="179"/><di:waypoint x="990" y="179"/></bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""


def build_tobe_bpmn(steps: list) -> str:
    s = [_esc(str(step).strip()[:40]) for step in (steps + [""] * 5)][:5]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn" id="Def_ToBe">
  <collaboration id="Collab_ToBe">
    <participant id="Pool_ToBe" name="To-Be: Целевой процесс" processRef="Proc_ToBe"/>
  </collaboration>
  <process id="Proc_ToBe" isExecutable="false">
    <startEvent id="TB_SE"  name="Триггер"><outgoing>TB_F1</outgoing></startEvent>
    <serviceTask id="TB_T1" name="{s[0]}"><incoming>TB_F1</incoming><outgoing>TB_F2</outgoing></serviceTask>
    <serviceTask id="TB_T2" name="{s[1]}"><incoming>TB_F2</incoming><outgoing>TB_F3</outgoing></serviceTask>
    <exclusiveGateway id="TB_GW" name="Проверка"><incoming>TB_F3</incoming><outgoing>TB_F4</outgoing><outgoing>TB_F5</outgoing></exclusiveGateway>
    <serviceTask id="TB_T3" name="{s[2]}"><incoming>TB_F4</incoming><outgoing>TB_F6</outgoing></serviceTask>
    <userTask   id="TB_T4" name="{s[3]}"><incoming>TB_F6</incoming><outgoing>TB_F7</outgoing></userTask>
    <serviceTask id="TB_T5" name="{s[4]}"><incoming>TB_F7</incoming><outgoing>TB_F8</outgoing></serviceTask>
    <endEvent   id="TB_EE1" name="Готово"><incoming>TB_F8</incoming></endEvent>
    <endEvent   id="TB_EE2" name="Отклонено"><incoming>TB_F5</incoming></endEvent>
    <sequenceFlow id="TB_F1" sourceRef="TB_SE"  targetRef="TB_T1"/>
    <sequenceFlow id="TB_F2" sourceRef="TB_T1"  targetRef="TB_T2"/>
    <sequenceFlow id="TB_F3" sourceRef="TB_T2"  targetRef="TB_GW"/>
    <sequenceFlow id="TB_F4" name="Ок"   sourceRef="TB_GW" targetRef="TB_T3"/>
    <sequenceFlow id="TB_F5" name="Нет"  sourceRef="TB_GW" targetRef="TB_EE2"/>
    <sequenceFlow id="TB_F6" sourceRef="TB_T3"  targetRef="TB_T4"/>
    <sequenceFlow id="TB_F7" sourceRef="TB_T4"  targetRef="TB_T5"/>
    <sequenceFlow id="TB_F8" sourceRef="TB_T5"  targetRef="TB_EE1"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiag_ToBe">
    <bpmndi:BPMNPlane id="BPMNPlane_ToBe" bpmnElement="Collab_ToBe">
      <bpmndi:BPMNShape id="Pool_ToBe_di" bpmnElement="Pool_ToBe" isHorizontal="true">
        <dc:Bounds x="100" y="80" width="1200" height="200"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_SE_di"  bpmnElement="TB_SE"><dc:Bounds x="152" y="161" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_T1_di"  bpmnElement="TB_T1"><dc:Bounds x="238" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_T2_di"  bpmnElement="TB_T2"><dc:Bounds x="388" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_GW_di"  bpmnElement="TB_GW" isMarkerVisible="true"><dc:Bounds x="538" y="155" width="50" height="50"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_T3_di"  bpmnElement="TB_T3"><dc:Bounds x="638" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_T4_di"  bpmnElement="TB_T4"><dc:Bounds x="788" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_T5_di"  bpmnElement="TB_T5"><dc:Bounds x="938" y="140" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_EE1_di" bpmnElement="TB_EE1"><dc:Bounds x="1090" y="161" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TB_EE2_di" bpmnElement="TB_EE2"><dc:Bounds x="545" y="92" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="TB_F1_di" bpmnElement="TB_F1"><di:waypoint x="188" y="179"/><di:waypoint x="238" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F2_di" bpmnElement="TB_F2"><di:waypoint x="338" y="179"/><di:waypoint x="388" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F3_di" bpmnElement="TB_F3"><di:waypoint x="488" y="179"/><di:waypoint x="538" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F4_di" bpmnElement="TB_F4"><di:waypoint x="588" y="179"/><di:waypoint x="638" y="179"/><bpmndi:BPMNLabel><dc:Bounds x="601" y="161" width="16" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F5_di" bpmnElement="TB_F5"><di:waypoint x="563" y="155"/><di:waypoint x="563" y="128"/><bpmndi:BPMNLabel><dc:Bounds x="569" y="138" width="24" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F6_di" bpmnElement="TB_F6"><di:waypoint x="738" y="179"/><di:waypoint x="788" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F7_di" bpmnElement="TB_F7"><di:waypoint x="888" y="179"/><di:waypoint x="938" y="179"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="TB_F8_di" bpmnElement="TB_F8"><di:waypoint x="1038" y="179"/><di:waypoint x="1090" y="179"/></bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""


# ---------------------------------------------------------------------------
# Demo content
# ---------------------------------------------------------------------------
DEMO_SPEC = """# Спецификация требований — Демо-режим

**Дата:** {date} | **Статус:** Демо | **Источник:** BAlance.ai

---

## 1. Бизнес-требования (Business Requirements)

**Цель:** Сократить время обработки заявок на 40% и устранить ручные операции в ключевых точках процесса.

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время обработки | 5–7 дней | < 2 дней |
| Доля ручного труда | ~70% | < 20% |
| Точность данных | 78% | > 95% |

---

## 2. Пользовательские требования (User Requirements)

**UC-01: Автоматизация сбора и валидации данных**

- **Предусловия:** Данные поступают из внешнего источника
- **Основной сценарий:** Система → Валидация → Уведомление исполнителя → Обработка → Запись в БД → Отчёт
- **Расширения:** При ошибке валидации — возврат на доработку с комментарием
- **Постусловия:** Запись сохранена, отчёт сформирован

---

## 3. Функциональные требования (Functional Requirements)

- **FR-01** Автоматическая валидация входящих данных по схеме
- **FR-02** Уведомления ответственным при отклонении от нормы
- **FR-03** Интеграция с корпоративной БД (REST API / webhook)
- **FR-04** Хранение полного аудит-лога всех изменений
- **FR-05** Экспорт отчётов в PDF / Excel

---

## 4. Нефункциональные требования (Non-Functional Requirements)

- **NFR-01 Производительность:** Обработка ≤ 3 сек при нагрузке до 500 запросов/мин
- **NFR-02 Безопасность:** Шифрование данных AES-256, авторизация OAuth 2.0
- **NFR-03 Доступность:** SLA ≥ 99.5% uptime
- **NFR-04 Интерфейс:** Адаптивный дизайн, время отклика UI < 200 мс
"""

DEMO_RTM = """# Матрица трассировки требований (RTM)

| ID | Тип | Описание | Приоритет |
|----|-----|----------|-----------|
| BR-01 | Бизнес | Сократить время обработки на 40% | Must |
| BR-02 | Бизнес | Устранить ручной ввод данных | Must |
| BR-03 | Бизнес | Повысить точность данных до 95% | Should |
| UR-01 | Пользователь | Автоматическая валидация при вводе | Must |
| UR-02 | Пользователь | Уведомления по email / push | Should |
| UR-03 | Пользователь | Просмотр истории изменений | Could |
| FR-01 | Функциональное | Валидация по JSON-схеме | Must |
| FR-02 | Функциональное | REST API интеграция с корп. БД | Must |
| FR-03 | Функциональное | Аудит-лог операций | Should |
| FR-04 | Функциональное | Экспорт PDF / Excel | Could |
| NFR-01 | Нефункциональное | Производительность ≤ 3 сек | Must |
| NFR-02 | Нефункциональное | Шифрование AES-256 | Must |
| NFR-03 | Нефункциональное | SLA ≥ 99.5% | Should |
| NFR-04 | Нефункциональное | Адаптивный UI | Could |
"""

DEMO_ASIS_STEPS = [
    "Ручной сбор данных",
    "Ввод в таблицу",
    "Согласование вручную",
    "Проверка руководителем",
    "Финальное утверждение",
]
DEMO_TOBE_STEPS = [
    "Авто-захват данных",
    "Системная валидация",
    "Авто-проверка правил",
    "Подтверждение менеджером",
    "Запись в БД и отчёт",
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM = """Ты — Senior Business Analyst с экспертизой в BPM, системном анализе и управлении требованиями. Работаешь с любыми таблицами бизнес-данных (не только CRM).

Тебе передан автоматический анализ таблицы. На его основе сгенерируй полную проектную документацию.

Ответ строго в следующем формате — четыре раздела, каждый начинается с маркера на отдельной строке:

STEPS_ASIS: Шаг 1 | Шаг 2 | Шаг 3 | Шаг 4 | Шаг 5
STEPS_TOBE: Шаг 1 | Шаг 2 | Шаг 3 | Шаг 4 | Шаг 5
SPEC:
[Полная спецификация требований в Markdown]
RTM:
[Матрица трассировки в Markdown]

Правила для STEPS_ASIS и STEPS_TOBE:
- Ровно 5 шагов, разделённых символом '|'
- ASIS: названия отражают ТЕКУЩИЙ ручной/неэффективный процесс (2-4 слова каждый)
- TOBE: названия отражают ЦЕЛЕВОЙ автоматизированный процесс (2-4 слова каждый)

Правила для SPEC (строго по 4 уровням, Markdown):

# Спецификация требований

**Дата:** [сегодня] | **Источник:** BAlance.ai

## 1. Бизнес-требования (Business Requirements)
[Цель, бизнес-эффект, таблица метрик As-Is vs To-Be с конкретными цифрами]

## 2. Пользовательские требования (User Requirements)
[UC по Коберну: ID, Предусловия, Основной сценарий таблицей Актор/Действие/Результат, Расширения, Постусловия]

## 3. Функциональные требования (Functional Requirements)
[Список FR-XX с конкретными функциями системы: валидация, интеграции, уведомления, хранение]

## 4. Нефункциональные требования (Non-Functional Requirements)
[NFR-XX: Производительность, Безопасность, Доступность, Интерфейс — с конкретными метриками]

Правила для RTM (строго Markdown-таблица):

# Матрица трассировки требований (RTM)

| ID | Тип | Описание | Приоритет |
|----|-----|----------|-----------|
[Минимум 12 строк: BR, UR, FR, NFR с приоритетами Must / Should / Could по методологии MoSCoW]

ВАЖНО: Никаких пояснений вне четырёх разделов. Маркеры STEPS_ASIS:, STEPS_TOBE:, SPEC:, RTM: — строго на отдельных строках."""


def _build_prompt(context_str: str, user_problem: str, insights: list) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    insight_str = " ".join(insights[:5]) if insights else ""
    problem_part = ""
    if user_problem.strip():
        problem_part = f" Задача от пользователя: {user_problem.strip()}."
    return (
        f"Сегодня: {today}. {context_str}{problem_part} "
        f"Ключевые наблюдения: {insight_str}"
    ).strip()


def _parse_ai_response(text: str) -> dict:
    def extract(marker, text):
        pattern = rf"^{re.escape(marker)}\s*\n([\s\S]+?)(?=\n(?:STEPS_ASIS|STEPS_TOBE|SPEC|RTM):|$)"
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    def extract_inline(marker, text):
        m = re.search(rf"^{re.escape(marker)}\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    asis_raw  = extract_inline("STEPS_ASIS:", text)
    tobe_raw  = extract_inline("STEPS_TOBE:", text)
    spec_text = extract("SPEC:", text)
    rtm_text  = extract("RTM:", text)

    def parse_steps(raw):
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        while len(parts) < 5:
            parts.append(f"Шаг {len(parts) + 1}")
        return parts[:5]

    return {
        "asis_steps": parse_steps(asis_raw),
        "tobe_steps": parse_steps(tobe_raw),
        "spec":       spec_text or "",
        "rtm":        rtm_text or "",
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
        temperature=0.4,
        max_tokens=2500,
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

    analysis = {}
    file_stats = None
    if df is not None:
        analysis = analyze_dataframe(df)
        file_stats = {
            "rows": analysis["total_rows"],
            "columns": analysis["column_names"],
            "insights": analysis["insights"],
        }

    context_str = analysis.get("context_str", "")
    insights    = analysis.get("insights", [])

    client, _ = get_ai_client()
    is_demo    = client is None
    demo_reason = None

    if is_demo:
        ai = None
        demo_reason = "GROQ_API_KEY не задан — активирован демо-режим"
    else:
        try:
            ai = _call_ai(context_str, problem, insights)
            if not ai or not ai.get("spec"):
                ai = None
                is_demo = True
                demo_reason = "AI вернул пустой ответ — показан шаблон"
        except Exception as e:
            ai = None
            is_demo = True
            demo_reason = f"Ошибка AI: {e}"

    today = datetime.now().strftime("%d.%m.%Y")
    if ai:
        asis_steps = ai["asis_steps"]
        tobe_steps = ai["tobe_steps"]
        spec       = ai["spec"]
        rtm        = ai["rtm"]
    else:
        asis_steps = DEMO_ASIS_STEPS
        tobe_steps = DEMO_TOBE_STEPS
        spec       = DEMO_SPEC.format(date=today)
        rtm        = DEMO_RTM

    return JSONResponse({
        "bpmn_asis":   build_asis_bpmn(asis_steps),
        "bpmn_tobe":   build_tobe_bpmn(tobe_steps),
        "spec":        spec,
        "rtm":         rtm,
        "demo":        is_demo,
        "demo_reason": demo_reason,
        "file_stats":  file_stats,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
