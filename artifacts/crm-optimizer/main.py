import os
import re
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd

app = FastAPI(title="BAlance.ai — CRM Streamlining & Funnel Architecture")
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
# BPMN XML template — stable, 100% renders in bpmn-js with all edges
# ---------------------------------------------------------------------------
def build_bpmn_xml(step1: str, step2: str) -> str:
    s1 = step1.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    s2 = step2.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_1">
  <collaboration id="Collaboration_1">
    <participant id="Pool_Manager" name="Менеджер / CRM-система" processRef="Process_Manager"/>
  </collaboration>
  <process id="Process_Manager" isExecutable="false">
    <startEvent id="SE1" name="Триггер&#10;сделки">
      <outgoing>F1</outgoing>
    </startEvent>
    <userTask id="T1" name="{s1}">
      <incoming>F1</incoming>
      <outgoing>F2</outgoing>
    </userTask>
    <exclusiveGateway id="GW1" name="Квалифицирован?">
      <incoming>F2</incoming>
      <outgoing>F3</outgoing>
      <outgoing>F4</outgoing>
    </exclusiveGateway>
    <serviceTask id="T2" name="{s2}">
      <incoming>F3</incoming>
      <outgoing>F5</outgoing>
    </serviceTask>
    <serviceTask id="T3" name="Обновить CRM&#10;и аналитику">
      <incoming>F5</incoming>
      <outgoing>F6</outgoing>
    </serviceTask>
    <exclusiveGateway id="GW2" name="Сделка&#10;закрыта?">
      <incoming>F6</incoming>
      <outgoing>F7</outgoing>
      <outgoing>F8</outgoing>
    </exclusiveGateway>
    <endEvent id="EE1" name="Выиграна">
      <incoming>F7</incoming>
    </endEvent>
    <endEvent id="EE2" name="Нецелевой">
      <incoming>F4</incoming>
    </endEvent>
    <endEvent id="EE3" name="Дозревание">
      <incoming>F8</incoming>
    </endEvent>
    <sequenceFlow id="F1" sourceRef="SE1"  targetRef="T1"/>
    <sequenceFlow id="F2" sourceRef="T1"   targetRef="GW1"/>
    <sequenceFlow id="F3" name="Да"  sourceRef="GW1" targetRef="T2"/>
    <sequenceFlow id="F4" name="Нет" sourceRef="GW1" targetRef="EE2"/>
    <sequenceFlow id="F5" sourceRef="T2"   targetRef="T3"/>
    <sequenceFlow id="F6" sourceRef="T3"   targetRef="GW2"/>
    <sequenceFlow id="F7" name="Да"  sourceRef="GW2" targetRef="EE1"/>
    <sequenceFlow id="F8" name="Нет" sourceRef="GW2" targetRef="EE3"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_1">
      <bpmndi:BPMNShape id="Pool_Manager_di" bpmnElement="Pool_Manager" isHorizontal="true">
        <dc:Bounds x="100" y="80" width="1020" height="200"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="SE1_di" bpmnElement="SE1">
        <dc:Bounds x="152" y="162" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="138" y="205" width="64" height="27"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T1_di" bpmnElement="T1">
        <dc:Bounds x="238" y="140" width="110" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW1_di" bpmnElement="GW1" isMarkerVisible="true">
        <dc:Bounds x="398" y="155" width="50" height="50"/>
        <bpmndi:BPMNLabel><dc:Bounds x="382" y="212" width="82" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T2_di" bpmnElement="T2">
        <dc:Bounds x="498" y="140" width="110" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T3_di" bpmnElement="T3">
        <dc:Bounds x="658" y="140" width="110" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW2_di" bpmnElement="GW2" isMarkerVisible="true">
        <dc:Bounds x="818" y="155" width="50" height="50"/>
        <bpmndi:BPMNLabel><dc:Bounds x="804" y="212" width="78" height="27"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE1_di" bpmnElement="EE1">
        <dc:Bounds x="920" y="162" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="910" y="205" width="56" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE2_di" bpmnElement="EE2">
        <dc:Bounds x="405" y="92" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="393" y="135" width="60" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE3_di" bpmnElement="EE3">
        <dc:Bounds x="825" y="92" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="811" y="135" width="64" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="F1_di" bpmnElement="F1">
        <di:waypoint x="188" y="180"/>
        <di:waypoint x="238" y="180"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F2_di" bpmnElement="F2">
        <di:waypoint x="348" y="180"/>
        <di:waypoint x="398" y="180"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F3_di" bpmnElement="F3">
        <di:waypoint x="448" y="180"/>
        <di:waypoint x="498" y="180"/>
        <bpmndi:BPMNLabel><dc:Bounds x="465" y="162" width="16" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F4_di" bpmnElement="F4">
        <di:waypoint x="423" y="155"/>
        <di:waypoint x="423" y="128"/>
        <bpmndi:BPMNLabel><dc:Bounds x="429" y="138" width="24" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F5_di" bpmnElement="F5">
        <di:waypoint x="608" y="180"/>
        <di:waypoint x="658" y="180"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F6_di" bpmnElement="F6">
        <di:waypoint x="768" y="180"/>
        <di:waypoint x="818" y="180"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F7_di" bpmnElement="F7">
        <di:waypoint x="868" y="180"/>
        <di:waypoint x="920" y="180"/>
        <bpmndi:BPMNLabel><dc:Bounds x="886" y="162" width="16" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F8_di" bpmnElement="F8">
        <di:waypoint x="843" y="155"/>
        <di:waypoint x="843" y="128"/>
        <bpmndi:BPMNLabel><dc:Bounds x="849" y="138" width="24" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""


# ---------------------------------------------------------------------------
# Demo assets
# ---------------------------------------------------------------------------
MOCK_USE_CASE = """# UC-01: Оптимизация конверсии на этапе Квалификации

**Дата:** {date} | **Статус:** Демо-режим | **Автор:** BAlance.ai

---

## Контекст / Цель

Выявление коренных причин (Root Cause Analysis) потери сделок на ранних этапах и предиктивное управление воронкой. Цель — снизить долю зависших сделок на этапе квалификации и автоматизировать эскалацию.

## Главный Актор

**Системный триггер** / Менеджер по продажам CRM

## Предусловия

- Сделка переведена в статус "Квалификация"
- Система зафиксировала отсутствие активности более 24 часов
- Менеджер авторизован в CRM с соответствующими правами

---

## Основной сценарий (Системные шаги)

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | Система | Считывает логи изменения статусов сделки из БД | Получен журнал активности |
| 2 | Система | Автоматически вычисляет метрику Days_In_Stage и сравнивает с SLA этапа | Выявлено превышение лимита |
| 3 | Система | Инициирует скрипт валидации причин потери (Lost Reason) | Запрос отправлен менеджеру |
| 4 | Менеджер | Выбирает формализованную причину из динамического справочника CRM | Причина зафиксирована |
| 5 | Система | Логирует изменения, пересчитывает конверсию воронки, отправляет событие в модуль аналитики | Данные актуализированы |

## Расширения и альтернативные сценарии

**Данные заполнены некорректно:** Система выводит предупреждение и блокирует сохранение до устранения ошибок валидации.

**Отсутствует интеграция с телефонией:** Система помечает сделку флагом «Нет данных о контактах», эскалирует руководителю через 48 ч.

**Отсутствует интеграция с мессенджерами:** Используется резервный канал — email-уведомление с требованием актуализировать статус.

## Постусловия

- Статус сделки обновлён в БД
- В CRM сгенерирована предиктивная задача на удержание клиента
- Метрики воронки пересчитаны и отправлены в дашборд аналитики

---

## Бизнес-правила

| Код | Правило |
|-----|---------|
| BR-01 | SLA первого контакта — не более **2 часов** |
| BR-02 | Days_In_Stage > 3 дней → автоматическая эскалация |
| BR-03 | КП направляется в течение **24 часов** после квалификации |
| BR-04 | Лид без активности **14 дней** → перевод в «Дозревание» |

## Метрики успеха (KPI)

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время первого контакта | > 4 ч | < 2 ч |
| Конверсия лид → сделка | ~15% | > 28% |
| Сделки в «Зависании» | ~30% | < 8% |
| Потеря лидов (нецелевые) | ~20% | < 5% |
"""

# ---------------------------------------------------------------------------
# System prompt — Senior BA / Cockburn methodology
# ---------------------------------------------------------------------------
_SYSTEM = """Ты Senior Business Analyst с 15-летним опытом в CRM-трансформациях. Твой стиль: системное мышление, Root Cause Analysis, методология Алистера Коберна.

Пользователь описывает проблему в CRM-процессе. Твоя задача — создать два артефакта.

Ответ строго в формате (три части, разделённые символом '|'):

Название шага 1 (2-4 слова) | Название шага 2 (2-4 слова) | Use Case

Use Case пиши на русском языке строго по следующей структуре Markdown:

# UC-[N]: [Динамическое название на основе этапа воронки из данных]

**Дата:** [сегодня] | **Источник:** BAlance.ai

## Контекст / Цель
[Root Cause Analysis проблемы. Что конкретно ломается в воронке и почему.]

## Главный Актор
[Системный триггер / роль менеджера]

## Предусловия
- [условие 1]
- [условие 2]

## Основной сценарий (Системные шаги)

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | Система | [автоматическое системное действие] | [результат] |
| 2 | Система | [вычисление метрики Days_In_Stage или аналог] | [результат] |
| 3 | Система | [инициация скрипта валидации или триггера] | [результат] |
| 4 | Менеджер | [формализованное действие в CRM] | [результат] |
| 5 | Система | [логирование, пересчёт конверсии, событие в аналитику] | [результат] |

## Расширения и альтернативные сценарии
[Поведение если данные некорректны или нет интеграции с телефонией / мессенджерами]

## Постусловия
- Статус сделки обновлён в БД
- В CRM сгенерирована предиктивная задача
- [ещё одно постусловие]

## Бизнес-правила (SLA)
| Код | Правило |
|-----|---------|
| BR-01 | [правило с конкретными цифрами] |
| BR-02 | [правило] |
| BR-03 | [правило] |

## Метрики успеха (KPI)
| Метрика | As-Is | To-Be |
|---------|-------|-------|
| [метрика] | [текущее] | [целевое] |
| [метрика] | [текущее] | [целевое] |
| [метрика] | [текущее] | [целевое] |

ВАЖНО: Ровно два символа '|' разделяют три части ответа. Никаких пояснений до первого '|' и после Use Case."""


def _build_prompt(df, problem: str) -> str:
    prob = problem.strip() or "Оптимизируй типовой процесс квалификации лидов в CRM."
    today = datetime.now().strftime("%d.%m.%Y")
    if df is not None:
        columns_str = ", ".join(list(df.columns)[:20])
        total_rows = len(df)
        stage_col = next(
            (c for c in df.columns if any(k in c.lower() for k in ["stage", "статус", "status", "этап", "phase"])),
            None,
        )
        funnel = ""
        if stage_col:
            unique_stages = ", ".join(str(v) for v in df[stage_col].dropna().unique()[:10])
            funnel = f" Этапы воронки ({stage_col}): {unique_stages}."
        return f"Сегодня: {today}. Проблема: {prob}. Колонки CRM: {columns_str}. Строк: {total_rows}.{funnel}"
    return f"Сегодня: {today}. Проблема: {prob}."


def _parse_pipe_response(text: str):
    parts = text.split("|", 2)
    if len(parts) >= 3:
        step1 = parts[0].strip()[:60]
        step2 = parts[1].strip()[:60]
        use_case = parts[2].strip()
        return step1, step2, use_case
    elif len(parts) == 2:
        step1 = parts[0].strip()[:60]
        step2 = parts[1].strip()[:60]
        return step1, step2, ""
    return "Квалификация лида", "Автоматизация CRM", text.strip()


def _call_ai(df, problem: str):
    client, model = get_ai_client()
    if client is None:
        return None, None
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(df, problem)},
        ],
        temperature=0.4,
        max_tokens=2000,
    )
    ai_response = str(resp.choices[0].message.content)
    step1, step2, use_case = _parse_pipe_response(ai_response)
    bpmn_xml = build_bpmn_xml(step1, step2)
    return bpmn_xml, use_case


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
                return JSONResponse({"error": f"Ошибка чтения Excel-файла: {e}"}, status_code=400)
        elif fname.endswith(".csv"):
            try:
                file.file.seek(0)
                df = pd.read_csv(file.file)
            except Exception as e:
                return JSONResponse({"error": f"Ошибка чтения CSV-файла: {e}"}, status_code=400)
        else:
            return JSONResponse(
                {"error": "Неверный формат. Поддерживаются только .csv, .xls, .xlsx."},
                status_code=400,
            )

    file_stats = None
    if df is not None:
        file_stats = {"rows": len(df), "columns": list(df.columns)}

    client, model = get_ai_client()
    if client is None:
        bpmn_xml = build_bpmn_xml("Квалификация лида", "Автоматизация CRM")
        use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
        is_demo = True
        demo_reason = "GROQ_API_KEY не задан — активирован демо-режим"
    else:
        try:
            bpmn_xml, use_case = _call_ai(df, problem)
            if not bpmn_xml:
                bpmn_xml = build_bpmn_xml("Квалификация лида", "Автоматизация CRM")
                use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
                is_demo = True
                demo_reason = "AI вернул пустой ответ — показан шаблон"
            else:
                is_demo = False
                demo_reason = None
        except Exception as e:
            bpmn_xml = build_bpmn_xml("Квалификация лида", "Автоматизация CRM")
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
