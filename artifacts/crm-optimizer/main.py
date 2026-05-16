import os
import re
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd

app = FastAPI(title="CRM Process Optimizer")
_HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")

# ---------------------------------------------------------------------------
# AI client — Groq preferred, OpenAI as fallback, demo mode if neither set
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
            client = _OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
            )
            return client, "llama-3.1-8b-instant"
    except Exception:
        pass
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            client = _OpenAI(api_key=openai_key)
            return client, "gpt-4o"
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# BPMN XML template — stable, always renders in bpmn-js
# ---------------------------------------------------------------------------
def build_bpmn_xml(step1: str, step2: str, step3: str = "Закрыть сделку") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn" id="Definitions_1">
  <collaboration id="Collaboration_1">
    <participant id="Pool_Manager" name="Менеджер по продажам" processRef="Process_Manager"/>
    <participant id="Pool_CRM"     name="CRM-система"          processRef="Process_CRM"/>
  </collaboration>
  <process id="Process_Manager" isExecutable="false">
    <startEvent id="SE1" name="Новая заявка"><outgoing>F1</outgoing></startEvent>
    <userTask   id="T1"  name="{step1}"><incoming>F1</incoming><outgoing>F2</outgoing></userTask>
    <exclusiveGateway id="GW1" name="Квалифицирован?"><incoming>F2</incoming><outgoing>F3</outgoing><outgoing>F4</outgoing></exclusiveGateway>
    <userTask   id="T2"  name="{step2}"><incoming>F3</incoming><outgoing>F5</outgoing></userTask>
    <userTask   id="T3"  name="{step3}"><incoming>F5</incoming><outgoing>F6</outgoing></userTask>
    <exclusiveGateway id="GW2" name="Сделка закрыта?"><incoming>F6</incoming><outgoing>F7</outgoing><outgoing>F8</outgoing></exclusiveGateway>
    <endEvent   id="EE1" name="Выиграна"><incoming>F7</incoming></endEvent>
    <endEvent   id="EE2" name="Не квалифицирован"><incoming>F4</incoming></endEvent>
    <endEvent   id="EE3" name="Дозревание"><incoming>F8</incoming></endEvent>
    <sequenceFlow id="F1" sourceRef="SE1"  targetRef="T1"/>
    <sequenceFlow id="F2" sourceRef="T1"   targetRef="GW1"/>
    <sequenceFlow id="F3" name="Да"  sourceRef="GW1" targetRef="T2"/>
    <sequenceFlow id="F4" name="Нет" sourceRef="GW1" targetRef="EE2"/>
    <sequenceFlow id="F5" sourceRef="T2"   targetRef="T3"/>
    <sequenceFlow id="F6" sourceRef="T3"   targetRef="GW2"/>
    <sequenceFlow id="F7" name="Да"  sourceRef="GW2" targetRef="EE1"/>
    <sequenceFlow id="F8" name="Нет" sourceRef="GW2" targetRef="EE3"/>
  </process>
  <process id="Process_CRM" isExecutable="false">
    <startEvent  id="CS1" name="Регистрация заявки"><outgoing>CF1</outgoing></startEvent>
    <serviceTask id="CT1" name="Уведомить менеджера"><incoming>CF1</incoming><outgoing>CF2</outgoing></serviceTask>
    <serviceTask id="CT2" name="Рассчитать скоринг"><incoming>CF2</incoming><outgoing>CF3</outgoing></serviceTask>
    <serviceTask id="CT3" name="Обновить статус"><incoming>CF3</incoming><outgoing>CF4</outgoing></serviceTask>
    <serviceTask id="CT4" name="Сформировать отчёт"><incoming>CF4</incoming><outgoing>CF5</outgoing></serviceTask>
    <endEvent    id="CE1" name="Данные актуализированы"><incoming>CF5</incoming></endEvent>
    <sequenceFlow id="CF1" sourceRef="CS1" targetRef="CT1"/>
    <sequenceFlow id="CF2" sourceRef="CT1" targetRef="CT2"/>
    <sequenceFlow id="CF3" sourceRef="CT2" targetRef="CT3"/>
    <sequenceFlow id="CF4" sourceRef="CT3" targetRef="CT4"/>
    <sequenceFlow id="CF5" sourceRef="CT4" targetRef="CE1"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_1">
      <bpmndi:BPMNShape id="Pool_Manager_di" bpmnElement="Pool_Manager" isHorizontal="true">
        <dc:Bounds x="130" y="60" width="1000" height="200"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="SE1_di"  bpmnElement="SE1"><dc:Bounds x="182" y="142" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T1_di"   bpmnElement="T1"><dc:Bounds x="268" y="120" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW1_di"  bpmnElement="GW1" isMarkerVisible="true"><dc:Bounds x="418" y="135" width="50" height="50"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T2_di"   bpmnElement="T2"><dc:Bounds x="518" y="120" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T3_di"   bpmnElement="T3"><dc:Bounds x="668" y="120" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW2_di"  bpmnElement="GW2" isMarkerVisible="true"><dc:Bounds x="818" y="135" width="50" height="50"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE1_di"  bpmnElement="EE1"><dc:Bounds x="920" y="142" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE2_di"  bpmnElement="EE2"><dc:Bounds x="425" y="72"  width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE3_di"  bpmnElement="EE3"><dc:Bounds x="825" y="72"  width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="F1_di"  bpmnElement="F1"><di:waypoint x="218" y="160"/><di:waypoint x="268" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F2_di"  bpmnElement="F2"><di:waypoint x="368" y="160"/><di:waypoint x="418" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F3_di"  bpmnElement="F3"><di:waypoint x="468" y="160"/><di:waypoint x="518" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F4_di"  bpmnElement="F4"><di:waypoint x="443" y="135"/><di:waypoint x="443" y="108"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F5_di"  bpmnElement="F5"><di:waypoint x="618" y="160"/><di:waypoint x="668" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F6_di"  bpmnElement="F6"><di:waypoint x="768" y="160"/><di:waypoint x="818" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F7_di"  bpmnElement="F7"><di:waypoint x="868" y="160"/><di:waypoint x="920" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F8_di"  bpmnElement="F8"><di:waypoint x="843" y="135"/><di:waypoint x="843" y="108"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="Pool_CRM_di" bpmnElement="Pool_CRM" isHorizontal="true">
        <dc:Bounds x="130" y="290" width="1000" height="180"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CS1_di" bpmnElement="CS1"><dc:Bounds x="182" y="362" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT1_di" bpmnElement="CT1"><dc:Bounds x="268" y="340" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT2_di" bpmnElement="CT2"><dc:Bounds x="418" y="340" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT3_di" bpmnElement="CT3"><dc:Bounds x="568" y="340" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT4_di" bpmnElement="CT4"><dc:Bounds x="718" y="340" width="100" height="80"/></bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CE1_di" bpmnElement="CE1"><dc:Bounds x="870" y="362" width="36" height="36"/></bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="CF1_di" bpmnElement="CF1"><di:waypoint x="218" y="380"/><di:waypoint x="268" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF2_di" bpmnElement="CF2"><di:waypoint x="368" y="380"/><di:waypoint x="418" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF3_di" bpmnElement="CF3"><di:waypoint x="518" y="380"/><di:waypoint x="568" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF4_di" bpmnElement="CF4"><di:waypoint x="668" y="380"/><di:waypoint x="718" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF5_di" bpmnElement="CF5"><di:waypoint x="818" y="380"/><di:waypoint x="870" y="380"/></bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""


# ---------------------------------------------------------------------------
# Demo assets
# ---------------------------------------------------------------------------
MOCK_USE_CASE = """# Use Case: Оптимизированный процесс CRM (To-Be)

**Дата:** {date} | **Статус:** Демо-режим

---

## Акторы

| Актор | Тип | Описание |
|-------|-----|----------|
| Менеджер по продажам | Основной | Квалифицирует лид, ведёт переговоры, закрывает сделку |
| CRM-система | Вторичный | Регистрирует заявки, скоринг, обновляет статусы |
| Руководитель отдела | Вторичный | Мониторинг воронки и эскалации |

## Предусловия
- Новая заявка поступила из любого канала
- Менеджер авторизован в CRM

## Основной сценарий

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | CRM | Регистрирует заявку, присваивает ID | Лид создан |
| 2 | CRM | Рассчитывает скоринг | Оценка присвоена |
| 3 | CRM | Уведомляет менеджера (push + email) | Уведомление отправлено |
| 4 | Менеджер | Квалифицирует лид | Решение принято |
| 5 | Менеджер | Готовит ТЗ с клиентом | ТЗ утверждено |
| 6 | Менеджер | Проводит презентацию | Клиент заинтересован |
| 7 | Менеджер | Согласовывает и отправляет КП | КП выслано |
| 8 | Менеджер | Фиксирует результат в CRM | Сделка закрыта |
| 9 | CRM | Генерирует отчёт | Данные актуализированы |

## Альтернативные сценарии

**Лид не квалифицирован:** Менеджер переводит в «Нецелевой», CRM архивирует с задачей повторного контакта через 3 месяца.

**Клиент не готов к покупке:** Статус «Дозревание», CRM создаёт напоминание на установленную дату.

## Бизнес-правила

| Код | Правило |
|-----|---------|
| BR-01 | SLA первого контакта — не более **2 часов** |
| BR-02 | ТЗ согласовывается не позднее **5 рабочих дней** |
| BR-03 | КП направляется в течение **24 часов** после ТЗ |
| BR-04 | Лид без активности **14 дней** → эскалация руководителю |

## Метрики успеха

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время первого контакта | > 4 ч | < 2 ч |
| Конверсия лид → сделка | ~15% | > 25% |
| Время на этапе ТЗ | 7–10 дней | 3–5 дней |
| Потеря лидов | ~20% | < 5% |
"""

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
_SYSTEM = """Ты профессиональный бизнес-аналитик CRM. Пользователь опишет проблему в CRM-процессе.

Твой ответ должен быть строго в следующем формате — три части, разделённые символом '|':

Название шага 1 (2-3 слова) | Название шага 2 (2-3 слова) | Подробный Use Case по стандарту Коберна на русском языке (400 слов)

Пример:
Квалификация лида | Подготовить КП | # Use Case: ...

ВАЖНО:
- Никаких дополнительных пояснений до или после
- Ровно один символ '|' между шагом 1 и шагом 2, и ещё один '|' между шагом 2 и текстом Use Case
- Use Case пиши в формате Markdown"""


def _build_prompt(df, problem: str) -> str:
    prob = problem.strip() or "Создай типовой оптимизированный процесс для CRM."
    if df is not None:
        columns_str = ", ".join(list(df.columns)[:20])
        total_rows = len(df)
        stage_col = next(
            (c for c in df.columns if "stage" in c.lower() or "статус" in c.lower()),
            None,
        )
        funnel = ""
        if stage_col:
            unique_stages = ", ".join(str(v) for v in df[stage_col].dropna().unique()[:10])
            funnel = f" Этапы воронки ({stage_col}): {unique_stages}."
        return f"Проблема: {prob}. Колонки CRM: {columns_str}. Строк: {total_rows}.{funnel}"
    return f"Проблема: {prob}."


def _parse_pipe_response(text: str):
    """Parse pipe-separated response: step1 | step2 | use_case_text"""
    parts = text.split("|", 2)
    if len(parts) >= 3:
        step1 = parts[0].strip()[:50]
        step2 = parts[1].strip()[:50]
        use_case = parts[2].strip()
        return step1, step2, use_case
    elif len(parts) == 2:
        step1 = parts[0].strip()[:50]
        step2 = parts[1].strip()[:50]
        return step1, step2, ""
    return "Квалификация лида", "Подготовить КП", text.strip()


def _call_ai(df, problem: str):
    client, model = get_ai_client()
    if client is None:
        return None, None, None
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(df, problem)},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    ai_response = str(resp.choices[0].message.content)
    step1, step2, use_case = _parse_pipe_response(ai_response)
    bpmn_xml = build_bpmn_xml(step1, step2)
    return bpmn_xml, use_case, model


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
                return JSONResponse(
                    {"error": f"Ошибка чтения Excel-файла: {e}"},
                    status_code=400,
                )
        elif fname.endswith(".csv"):
            try:
                file.file.seek(0)
                df = pd.read_csv(file.file)
            except Exception as e:
                return JSONResponse(
                    {"error": f"Ошибка чтения CSV-файла: {e}"},
                    status_code=400,
                )
        else:
            return JSONResponse(
                {"error": "Неверный формат файла. Поддерживаются только .csv, .xls, .xlsx."},
                status_code=400,
            )

    # File stats for the response
    file_stats = None
    if df is not None:
        file_stats = {
            "rows": len(df),
            "columns": list(df.columns),
        }

    client, model = get_ai_client()
    if client is None:
        bpmn_xml = build_bpmn_xml("Квалификация лида", "Подготовить КП")
        use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
        is_demo = True
        demo_reason = "GROQ_API_KEY не задан — включён демо-режим"
    else:
        try:
            bpmn_xml, use_case, model_used = _call_ai(df, problem)
            if not bpmn_xml:
                bpmn_xml = build_bpmn_xml("Квалификация лида", "Подготовить КП")
                use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
                is_demo = True
                demo_reason = "AI вернул пустой ответ — показан шаблон"
            else:
                is_demo = False
                demo_reason = None
        except Exception as e:
            bpmn_xml = build_bpmn_xml("Квалификация лида", "Подготовить КП")
            use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
            is_demo = True
            demo_reason = f"Ошибка запроса к AI: {e}"

    return JSONResponse({
        "bpmn_xml": bpmn_xml,
        "use_case": use_case,
        "demo": is_demo,
        "demo_reason": demo_reason,
        "file_stats": file_stats,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
