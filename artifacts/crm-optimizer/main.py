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
# DATA MINING — automatic funnel analysis from the uploaded dataframe
# ---------------------------------------------------------------------------
def mine_dataframe(df: pd.DataFrame) -> dict:
    """
    Extract key funnel metrics from a CRM dataframe.
    Returns a dict with: conversion, bottleneck_stage, max_days, top_reason,
    auto_problem (summary string), and column_names.
    """
    cols_lower = {c: c.lower() for c in df.columns}

    result = {
        "conversion": None,
        "bottleneck_stage": None,
        "max_days": None,
        "top_reason": None,
        "auto_problem": None,
        "column_names": list(df.columns),
        "total_rows": len(df),
    }

    # --- Stage / status column ---
    stage_col = next(
        (c for c in df.columns if any(k in cols_lower[c] for k in
         ["stage", "стадия", "статус", "status", "этап", "phase"])),
        None,
    )
    if stage_col:
        total = len(df)
        won_keywords = ["closed won", "выиграна", "won", "закрыта", "closed", "выигран"]
        won_mask = df[stage_col].astype(str).str.lower().str.strip().isin(won_keywords)
        conversion = round(won_mask.sum() / total * 100, 1) if total > 0 else 0
        result["conversion"] = conversion

    # --- Days-in-stage column ---
    days_col = next(
        (c for c in df.columns if any(k in cols_lower[c] for k in
         ["days", "дни", "день", "duration", "time_in", "days_in"])),
        None,
    )
    if days_col and stage_col:
        try:
            df_copy = df[[stage_col, days_col]].copy()
            df_copy[days_col] = pd.to_numeric(df_copy[days_col], errors="coerce")
            avg_by_stage = df_copy.groupby(stage_col)[days_col].mean().dropna()
            if not avg_by_stage.empty:
                bottleneck_stage = avg_by_stage.idxmax()
                max_days = round(avg_by_stage.max(), 1)
                result["bottleneck_stage"] = str(bottleneck_stage)
                result["max_days"] = max_days
        except Exception:
            pass
    elif days_col:
        try:
            df[days_col] = pd.to_numeric(df[days_col], errors="coerce")
            result["max_days"] = round(df[days_col].mean(), 1)
        except Exception:
            pass

    # --- Rejection reason column ---
    reason_col = next(
        (c for c in df.columns if any(k in cols_lower[c] for k in
         ["reason", "причина", "lost_reason", "loss_reason", "rejection", "отказ"])),
        None,
    )
    if reason_col:
        try:
            counts = df[reason_col].dropna().astype(str).str.strip()
            counts = counts[counts != ""]
            if not counts.empty:
                result["top_reason"] = counts.value_counts().idxmax()
        except Exception:
            pass

    # --- Build auto_problem summary ---
    parts = []
    if result["conversion"] is not None:
        parts.append(f"Конверсия воронки составляет {result['conversion']}%")
    if result["bottleneck_stage"] and result["max_days"] is not None:
        parts.append(
            f"главное узкое место — этап '{result['bottleneck_stage']}', "
            f"где сделки зависают в среднем на {result['max_days']} дней"
        )
    elif result["max_days"] is not None:
        parts.append(f"среднее время сделки составляет {result['max_days']} дней")
    if result["top_reason"]:
        parts.append(f"основная причина отказов — «{result['top_reason']}»")

    if parts:
        result["auto_problem"] = ". ".join(p.capitalize() for p in parts) + "."

    return result


# ---------------------------------------------------------------------------
# BPMN XML template — stable, always renders in bpmn-js with all edges
# ---------------------------------------------------------------------------
def build_bpmn_xml(step1: str, step2: str) -> str:
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    s1 = esc(step1)
    s2 = esc(step2)
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

**Дата:** {date} | **Статус:** Демо-режим | **Источник:** BAlance.ai

---

## Контекст / Цель

Выявление коренных причин (Root Cause Analysis) потери сделок на ранних этапах и предиктивное управление воронкой. Цель — снизить долю зависших сделок и автоматизировать эскалацию.

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
| 2 | Система | Вычисляет метрику Days_In_Stage и сравнивает с SLA этапа | Выявлено превышение лимита |
| 3 | Система | Инициирует скрипт валидации причин потери (Lost Reason) | Запрос отправлен менеджеру |
| 4 | Менеджер | Выбирает формализованную причину из динамического справочника CRM | Причина зафиксирована |
| 5 | Система | Логирует изменения, пересчитывает конверсию, отправляет событие в аналитику | Данные актуализированы |

## Расширения и альтернативные сценарии

**Данные заполнены некорректно:** Система выводит предупреждение и блокирует сохранение до устранения ошибок валидации.

**Отсутствует интеграция с телефонией:** Система помечает сделку флагом «Нет данных о контактах», эскалирует руководителю через 48 ч.

**Отсутствует интеграция с мессенджерами:** Используется резервный канал — email-уведомление с требованием актуализировать статус.

## Постусловия

- Статус сделки обновлён в БД
- В CRM сгенерирована предиктивная задача на удержание клиента
- Метрики воронки пересчитаны и отправлены в дашборд аналитики

---

## Бизнес-правила (SLA)

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
# System prompt — Senior BA, Cockburn, data-driven
# ---------------------------------------------------------------------------
_SYSTEM = """Ты — Senior Business Analyst с 15-летним опытом CRM-трансформаций. Стиль: системное мышление, Root Cause Analysis, методология Коберна.

Тебе передан автоматический отчёт математического анализа воронки продаж. На его основе сгенерируй профессиональное ТЗ и Use Case по стандарту Коберна на русском языке.

Ответ строго в формате — три части, разделённые символом '|':

Название шага 1 (2-4 слова) | Название шага 2 (2-4 слова) | Use Case

Шаги должны отражать конкретный найденный бутылочный этап и автоматизацию его решения.

Use Case пиши строго по этой Markdown-структуре:

# UC-[N]: [Название, динамически отражающее найденный бутылочный этап воронки]

**Дата:** [сегодня] | **Источник:** BAlance.ai

## Контекст / Цель
[Root Cause Analysis — почему именно этот этап является узким местом, опираясь на переданные цифры]

## Главный Актор
[Системный триггер / роль менеджера]

## Предусловия
- [условие связанное с найденным этапом]
- [условие связанное с Days_In_Stage или конверсией]

## Основной сценарий (Системные шаги)

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | Система | [считывает логи / данные из БД] | [результат] |
| 2 | Система | [вычисляет Days_In_Stage для найденного бутылочного этапа] | [результат] |
| 3 | Система | [инициирует скрипт валидации или триггер автоматизации] | [результат] |
| 4 | Менеджер | [формализованное действие на основе найденной причины отказов] | [результат] |
| 5 | Система | [логирование, пересчёт конверсии, событие в аналитику] | [результат] |

## Расширения и альтернативные сценарии
[Поведение если данные некорректны или нет интеграции с телефонией / мессенджерами]

## Постусловия
- Статус сделки обновлён в БД
- В CRM сгенерирована предиктивная задача на удержание клиента
- [ещё одно постусловие, специфичное для найденной проблемы]

## Бизнес-правила (SLA)
| Код | Правило |
|-----|---------|
| BR-01 | [правило с конкретными цифрами из данных] |
| BR-02 | [правило о Days_In_Stage] |
| BR-03 | [правило о причинах отказов] |

## Метрики успеха (KPI)
| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Конверсия воронки | [из данных]% | [улучшенный таргет]% |
| Days_In_Stage (узкое место) | [из данных] дней | [сокращённый таргет] дней |
| [ещё метрика] | [текущее] | [целевое] |

ВАЖНО: Ровно два символа '|' делят ответ на три части. Никаких пояснений вне структуры."""


def _build_prompt(auto_problem: str, user_problem: str, columns: list, total_rows: int) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    cols_str = ", ".join(columns[:20])

    combined = auto_problem or ""
    if user_problem.strip():
        combined = (combined + " Дополнение от пользователя: " + user_problem.strip()).strip()
    if not combined:
        combined = "Оптимизируй типовой процесс квалификации лидов в CRM."

    return (
        f"Сегодня: {today}. "
        f"Автоматический анализ воронки: {combined} "
        f"Структура датасета: {total_rows} строк, колонки: {cols_str}."
    )


def _parse_pipe_response(text: str):
    parts = text.split("|", 2)
    if len(parts) >= 3:
        return parts[0].strip()[:60], parts[1].strip()[:60], parts[2].strip()
    if len(parts) == 2:
        return parts[0].strip()[:60], parts[1].strip()[:60], ""
    return "Квалификация лида", "Автоматизация CRM", text.strip()


def _call_ai(auto_problem: str, user_problem: str, columns: list, total_rows: int):
    client, model = get_ai_client()
    if client is None:
        return None, None
    prompt = _build_prompt(auto_problem, user_problem, columns, total_rows)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": prompt},
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

    # Guard: require at least a file or a problem description
    if df is None and not problem.strip():
        return JSONResponse(
            {"error": "Загрузите файл CRM-данных или введите описание проблемы."},
            status_code=400,
        )

    # ── Data Mining ──
    mining = {}
    auto_problem = ""
    file_stats = None
    if df is not None:
        mining = mine_dataframe(df)
        auto_problem = mining.get("auto_problem") or ""
        file_stats = {
            "rows": mining["total_rows"],
            "columns": mining["column_names"],
            "conversion": mining["conversion"],
            "bottleneck_stage": mining["bottleneck_stage"],
            "max_days": mining["max_days"],
            "top_reason": mining["top_reason"],
        }

    columns = mining.get("column_names", [])
    total_rows = mining.get("total_rows", 0)

    # ── AI call ──
    client, model = get_ai_client()
    if client is None:
        bpmn_xml = build_bpmn_xml("Квалификация лида", "Автоматизация CRM")
        use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
        is_demo = True
        demo_reason = "GROQ_API_KEY не задан — активирован демо-режим"
    else:
        try:
            bpmn_xml, use_case = _call_ai(auto_problem, problem, columns, total_rows)
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
        "bpmn_xml":   bpmn_xml,
        "use_case":   use_case,
        "demo":       is_demo,
        "demo_reason": demo_reason,
        "file_stats": file_stats,
        "auto_problem": auto_problem or None,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
