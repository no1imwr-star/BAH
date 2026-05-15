import os
import io
import json
import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

st.set_page_config(
    page_title="CRM Process Optimizer",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

MOCK_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_1">
  <collaboration id="Collaboration_1">
    <participant id="Pool_Manager" name="Менеджер по продажам" processRef="Process_Manager" />
    <participant id="Pool_CRM" name="CRM-система" processRef="Process_CRM" />
  </collaboration>

  <process id="Process_Manager" isExecutable="false">
    <startEvent id="StartEvent_1" name="Новая заявка получена">
      <outgoing>Flow_1</outgoing>
    </startEvent>
    <userTask id="Task_Qualify" name="Квалификация лида">
      <incoming>Flow_1</incoming>
      <outgoing>Flow_2</outgoing>
    </userTask>
    <exclusiveGateway id="Gateway_Qualified" name="Лид квалифицирован?">
      <incoming>Flow_2</incoming>
      <outgoing>Flow_3</outgoing>
      <outgoing>Flow_4</outgoing>
    </exclusiveGateway>
    <userTask id="Task_TZ" name="Подготовить ТЗ">
      <incoming>Flow_3</incoming>
      <outgoing>Flow_5</outgoing>
    </userTask>
    <userTask id="Task_Present" name="Провести презентацию решения">
      <incoming>Flow_5</incoming>
      <outgoing>Flow_6</outgoing>
    </userTask>
    <userTask id="Task_Negotiate" name="Согласовать условия и КП">
      <incoming>Flow_6</incoming>
      <outgoing>Flow_7</outgoing>
    </userTask>
    <exclusiveGateway id="Gateway_Deal" name="Сделка закрыта?">
      <incoming>Flow_7</incoming>
      <outgoing>Flow_8</outgoing>
      <outgoing>Flow_9</outgoing>
    </exclusiveGateway>
    <endEvent id="EndEvent_Won" name="Сделка выиграна">
      <incoming>Flow_8</incoming>
    </endEvent>
    <endEvent id="EndEvent_Lost" name="Сделка проиграна">
      <incoming>Flow_4</incoming>
    </endEvent>
    <endEvent id="EndEvent_Nurture" name="В работу на дозревание">
      <incoming>Flow_9</incoming>
    </endEvent>
    <sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_Qualify" />
    <sequenceFlow id="Flow_2" sourceRef="Task_Qualify" targetRef="Gateway_Qualified" />
    <sequenceFlow id="Flow_3" name="Да" sourceRef="Gateway_Qualified" targetRef="Task_TZ" />
    <sequenceFlow id="Flow_4" name="Нет" sourceRef="Gateway_Qualified" targetRef="EndEvent_Lost" />
    <sequenceFlow id="Flow_5" sourceRef="Task_TZ" targetRef="Task_Present" />
    <sequenceFlow id="Flow_6" sourceRef="Task_Present" targetRef="Task_Negotiate" />
    <sequenceFlow id="Flow_7" sourceRef="Task_Negotiate" targetRef="Gateway_Deal" />
    <sequenceFlow id="Flow_8" name="Да" sourceRef="Gateway_Deal" targetRef="EndEvent_Won" />
    <sequenceFlow id="Flow_9" name="Нет" sourceRef="Gateway_Deal" targetRef="EndEvent_Nurture" />
  </process>

  <process id="Process_CRM" isExecutable="false">
    <startEvent id="CRM_Start" name="Авто-регистрация заявки">
      <outgoing>CRM_Flow_1</outgoing>
    </startEvent>
    <serviceTask id="CRM_Task_Notify" name="Уведомить менеджера">
      <incoming>CRM_Flow_1</incoming>
      <outgoing>CRM_Flow_2</outgoing>
    </serviceTask>
    <serviceTask id="CRM_Task_Score" name="Рассчитать скоринг лида">
      <incoming>CRM_Flow_2</incoming>
      <outgoing>CRM_Flow_3</outgoing>
    </serviceTask>
    <serviceTask id="CRM_Task_Update" name="Обновить статус сделки">
      <incoming>CRM_Flow_3</incoming>
      <outgoing>CRM_Flow_4</outgoing>
    </serviceTask>
    <serviceTask id="CRM_Task_Report" name="Сформировать отчёт">
      <incoming>CRM_Flow_4</incoming>
      <outgoing>CRM_Flow_5</outgoing>
    </serviceTask>
    <endEvent id="CRM_End" name="Данные актуализированы">
      <incoming>CRM_Flow_5</incoming>
    </endEvent>
    <sequenceFlow id="CRM_Flow_1" sourceRef="CRM_Start" targetRef="CRM_Task_Notify" />
    <sequenceFlow id="CRM_Flow_2" sourceRef="CRM_Task_Notify" targetRef="CRM_Task_Score" />
    <sequenceFlow id="CRM_Flow_3" sourceRef="CRM_Task_Score" targetRef="CRM_Task_Update" />
    <sequenceFlow id="CRM_Flow_4" sourceRef="CRM_Task_Update" targetRef="CRM_Task_Report" />
    <sequenceFlow id="CRM_Flow_5" sourceRef="CRM_Task_Report" targetRef="CRM_End" />
  </process>

  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_1">
      <bpmndi:BPMNShape id="Pool_Manager_di" bpmnElement="Pool_Manager" isHorizontal="true">
        <dc:Bounds x="130" y="60" width="900" height="250" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="182" y="162" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="155" y="205" width="90" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Qualify_di" bpmnElement="Task_Qualify">
        <dc:Bounds x="270" y="140" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_Qualified_di" bpmnElement="Gateway_Qualified" isMarkerVisible="true">
        <dc:Bounds x="415" y="155" width="50" height="50" />
        <bpmndi:BPMNLabel><dc:Bounds x="398" y="212" width="84" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_TZ_di" bpmnElement="Task_TZ">
        <dc:Bounds x="510" y="140" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Present_di" bpmnElement="Task_Present">
        <dc:Bounds x="660" y="140" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Negotiate_di" bpmnElement="Task_Negotiate">
        <dc:Bounds x="810" y="140" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_Deal_di" bpmnElement="Gateway_Deal" isMarkerVisible="true">
        <dc:Bounds x="955" y="155" width="50" height="50" />
        <bpmndi:BPMNLabel><dc:Bounds x="938" y="212" width="84" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Won_di" bpmnElement="EndEvent_Won">
        <dc:Bounds x="1052" y="162" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="1030" y="205" width="80" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Lost_di" bpmnElement="EndEvent_Lost">
        <dc:Bounds x="422" y="82" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="398" y="60" width="84" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Nurture_di" bpmnElement="EndEvent_Nurture">
        <dc:Bounds x="962" y="82" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="938" y="60" width="84" height="40" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="218" y="180" /><di:waypoint x="270" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="370" y="180" /><di:waypoint x="415" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_3_di" bpmnElement="Flow_3">
        <di:waypoint x="465" y="180" /><di:waypoint x="510" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_4_di" bpmnElement="Flow_4">
        <di:waypoint x="440" y="155" /><di:waypoint x="440" y="118" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_5_di" bpmnElement="Flow_5">
        <di:waypoint x="610" y="180" /><di:waypoint x="660" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_6_di" bpmnElement="Flow_6">
        <di:waypoint x="760" y="180" /><di:waypoint x="810" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_7_di" bpmnElement="Flow_7">
        <di:waypoint x="910" y="180" /><di:waypoint x="955" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_8_di" bpmnElement="Flow_8">
        <di:waypoint x="1005" y="180" /><di:waypoint x="1052" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_9_di" bpmnElement="Flow_9">
        <di:waypoint x="980" y="155" /><di:waypoint x="980" y="118" />
      </bpmndi:BPMNEdge>

      <bpmndi:BPMNShape id="Pool_CRM_di" bpmnElement="Pool_CRM" isHorizontal="true">
        <dc:Bounds x="130" y="340" width="900" height="200" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_Start_di" bpmnElement="CRM_Start">
        <dc:Bounds x="182" y="422" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="155" y="465" width="90" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_Task_Notify_di" bpmnElement="CRM_Task_Notify">
        <dc:Bounds x="270" y="400" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_Task_Score_di" bpmnElement="CRM_Task_Score">
        <dc:Bounds x="420" y="400" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_Task_Update_di" bpmnElement="CRM_Task_Update">
        <dc:Bounds x="570" y="400" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_Task_Report_di" bpmnElement="CRM_Task_Report">
        <dc:Bounds x="720" y="400" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CRM_End_di" bpmnElement="CRM_End">
        <dc:Bounds x="872" y="422" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="845" y="465" width="90" height="27" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="CRM_Flow_1_di" bpmnElement="CRM_Flow_1">
        <di:waypoint x="218" y="440" /><di:waypoint x="270" y="440" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CRM_Flow_2_di" bpmnElement="CRM_Flow_2">
        <di:waypoint x="370" y="440" /><di:waypoint x="420" y="440" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CRM_Flow_3_di" bpmnElement="CRM_Flow_3">
        <di:waypoint x="520" y="440" /><di:waypoint x="570" y="440" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CRM_Flow_4_di" bpmnElement="CRM_Flow_4">
        <di:waypoint x="670" y="440" /><di:waypoint x="720" y="440" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CRM_Flow_5_di" bpmnElement="CRM_Flow_5">
        <di:waypoint x="820" y="440" /><di:waypoint x="872" y="440" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""

MOCK_USE_CASE = """# Use Case: Оптимизированный процесс работы с CRM (To-Be)

---

## Use Case: UC-001 — Квалификация и обработка лида в CRM

**Версия:** 1.0  
**Дата:** {date}  
**Статус:** Черновик (Demo Mode)

---

### 1. Название
Полный цикл обработки лида: от регистрации до закрытия сделки

### 2. Акторы
| Актор | Тип | Описание |
|-------|-----|----------|
| Менеджер по продажам | Основной | Квалифицирует лид, ведёт переговоры, закрывает сделку |
| CRM-система | Вторичный | Регистрирует заявки, рассчитывает скоринг, обновляет статусы |
| Руководитель отдела продаж | Вторичный | Просматривает отчёты и контролирует воронку |

### 3. Предусловия
- Новая заявка (лид) поступила из любого канала (сайт, почта, звонок, реферал)
- Менеджер авторизован в CRM-системе
- CRM-система функционирует в штатном режиме

### 4. Основной сценарий (Happy Path)

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | CRM-система | Автоматически регистрирует входящую заявку и присваивает уникальный ID | Лид создан в системе |
| 2 | CRM-система | Рассчитывает скоринг лида на основе источника и данных профиля | Скоринговая оценка присвоена |
| 3 | CRM-система | Уведомляет ответственного менеджера (push + email) | Менеджер получает уведомление |
| 4 | Менеджер | Открывает карточку лида в CRM, изучает скоринг и источник | Принято решение о квалификации |
| 5 | Менеджер | Проводит первичный контакт (звонок / письмо) и оценивает соответствие ICP | Лид квалифицирован как целевой |
| 6 | Менеджер | Переводит лид в статус «В работе», заполняет ключевые поля | Статус обновлён в CRM |
| 7 | Менеджер | Готовит и согласовывает ТЗ (технические требования) с клиентом | ТЗ утверждено |
| 8 | Менеджер | Проводит презентацию решения | Клиент заинтересован |
| 9 | Менеджер | Формирует и отправляет коммерческое предложение | КП выслано клиенту |
| 10 | Менеджер | Проводит переговоры, согласовывает условия | Условия согласованы |
| 11 | Менеджер | Фиксирует результат сделки в CRM | Сделка закрыта как «Выиграна» |
| 12 | CRM-система | Генерирует итоговый отчёт по сделке | Данные актуализированы |

### 5. Альтернативные сценарии

#### 5.1 Лид не прошёл квалификацию (Шаг 5)
- **Условие:** Потребности клиента не соответствуют предложению компании
- **Действие:** Менеджер переводит лид в статус «Нецелевой» с указанием причины
- **Результат:** CRM автоматически архивирует лид; при необходимости — ставится задача на повторный контакт через 3 месяца

#### 5.2 Клиент не готов к покупке (Шаг 10)
- **Условие:** Клиент заинтересован, но не готов принять решение сейчас
- **Действие:** Менеджер переводит лид в статус «Дозревание», устанавливает дату следующего контакта
- **Результат:** CRM создаёт напоминание; лид остаётся в воронке с пониженным приоритетом

#### 5.3 Сбой CRM на любом шаге
- **Условие:** CRM-система недоступна
- **Действие:** Менеджер фиксирует данные в резервной форме (Google Sheets / бумажный носитель); системный администратор получает алерт
- **Результат:** После восстановления системы менеджер переносит данные; инцидент логируется

### 6. Постусловия
- Сделка имеет финальный статус («Выиграна», «Проиграна», «Дозревание»)
- Все взаимодействия с клиентом зафиксированы в истории лида
- CRM-отчёт сформирован и доступен руководителю
- KPI менеджера обновлены автоматически

### 7. Бизнес-правила
- **BR-01:** SLA первого контакта — не более 2 часов с момента поступления заявки
- **BR-02:** ТЗ должно быть согласовано не позднее 5 рабочих дней с начала переговоров
- **BR-03:** КП направляется клиенту в течение 24 часов после утверждения ТЗ
- **BR-04:** Лид без активности более 14 дней автоматически эскалируется руководителю

### 8. Метрики успеха
| Метрика | Текущее (As-Is) | Целевое (To-Be) |
|---------|-----------------|-----------------|
| Время первого контакта | > 4 часов | < 2 часов |
| Конверсия лид → сделка | ~15% | > 25% |
| Среднее время на этапе ТЗ | 7–10 дней | 3–5 дней |
| Потеря лидов из-за задержек | ~20% | < 5% |

---
*Документ сгенерирован CRM Process Optimizer в демо-режиме. Для персонализированного анализа введите OpenAI API Key и загрузите данные.*
"""


def get_openai_client():
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", None)
    if api_key and OPENAI_AVAILABLE:
        return OpenAI(api_key=api_key)
    return None


def build_system_prompt():
    return """Ты — эксперт по бизнес-процессам, CRM-системам и методологии BPMN 2.0.
Твоя задача — проанализировать структуру CRM-данных и описание проблемы, затем выдать два результата строго в формате JSON.

ВАЖНО: Ответь ТОЛЬКО валидным JSON без markdown-блоков, без пояснений, без пропусков.

Формат ответа:
{
  "bpmn_xml": "<полный BPMN 2.0 XML>",
  "use_case": "<полный Use Case в Markdown>"
}

Требования к BPMN XML:
- Валидный BPMN 2.0 XML, который открывается bpmn-js без ошибок
- Два пула (Pools): "Менеджер по продажам" и "CRM-система"
- В каждом пуле — дорожки (Lanes) при необходимости
- Задачи (Tasks), шлюзы (Gateways), события Start/End
- Полная секция BPMNDiagram с координатами (BPMNShape и BPMNEdge)
- Все ID уникальны, все ссылки корректны

Требования к Use Case (стандарт Коберна):
- Название, Акторы (таблица), Предусловия
- Основной сценарий (нумерованные шаги в таблице: Шаг | Актор | Действие | Результат)
- Альтернативные сценарии (минимум 2)
- Постусловия
- Бизнес-правила (BR-XX)
- Форматирование в Markdown с таблицами"""


def build_user_prompt(df, problem_text):
    columns_info = ""
    if df is not None:
        columns_info = f"""
Структура загруженных CRM-данных:
- Количество строк: {len(df)}
- Колонки: {', '.join(df.columns.tolist())}
- Примеры значений:
{df.head(3).to_string()}

Возможные этапы воронки: {', '.join([str(v) for v in df.iloc[:, -1].unique()[:10]] if len(df.columns) > 0 else [])}
"""

    return f"""Проанализируй следующие данные и проблему, затем создай оптимизированный процесс "To-Be".

{columns_info}

Описание проблемы от бизнес-аналитика:
{problem_text if problem_text else "Не указано. Создай типовой оптимизированный процесс для CRM."}

Сгенерируй:
1. BPMN 2.0 XML схему процесса "To-Be" с пулами Менеджера и CRM-системы
2. Use Case по стандарту Коберна с таблицами в Markdown

Ответь строго в формате JSON: {{"bpmn_xml": "...", "use_case": "..."}}"""


def call_openai(client, df, problem_text):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(df, problem_text)},
        ],
        temperature=0.3,
        max_tokens=6000,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    result = json.loads(content)
    return result.get("bpmn_xml", ""), result.get("use_case", "")


def render_bpmn_viewer(bpmn_xml):
    escaped = bpmn_xml.replace("`", "\\`").replace("\\", "\\\\").replace("$", "\\$")
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; background: #f8f9fa; }}
    #canvas {{ width: 100%; height: 580px; background: #fff; border: 1px solid #dee2e6; border-radius: 6px; }}
    #controls {{
      position: absolute; top: 10px; right: 10px; z-index: 10;
      display: flex; gap: 6px;
    }}
    .btn {{
      padding: 6px 12px; background: #fff; border: 1px solid #ced4da;
      border-radius: 4px; cursor: pointer; font-size: 13px; font-family: sans-serif;
      box-shadow: 0 1px 3px rgba(0,0,0,.1);
    }}
    .btn:hover {{ background: #f1f3f5; }}
    #error-msg {{
      display: none; padding: 12px 16px; background: #fff3cd;
      border: 1px solid #ffc107; border-radius: 6px; margin: 8px;
      font-family: sans-serif; font-size: 13px; color: #856404;
    }}
    #container {{ position: relative; width: 100%; }}
  </style>
</head>
<body>
<div id="container">
  <div id="controls">
    <button class="btn" onclick="zoomIn()">+</button>
    <button class="btn" onclick="zoomOut()">−</button>
    <button class="btn" onclick="fitView()">По размеру</button>
    <button class="btn" onclick="resetZoom()">1:1</button>
  </div>
  <div id="error-msg" id="err"></div>
  <div id="canvas"></div>
</div>

<script src="https://unpkg.com/bpmn-js@17.2.1/dist/bpmn-viewer.development.js"></script>
<script>
  var viewer = new BpmnJS({{ container: '#canvas' }});
  var xml = `{escaped}`;

  viewer.importXML(xml).then(function(result) {{
    if (result.warnings && result.warnings.length > 0) {{
      console.warn('BPMN warnings:', result.warnings);
    }}
    viewer.get('canvas').zoom('fit-viewport', 'auto');
  }}).catch(function(err) {{
    var errDiv = document.getElementById('error-msg');
    errDiv.style.display = 'block';
    errDiv.textContent = 'Ошибка рендеринга BPMN: ' + err.message;
    console.error('BPMN import error:', err);
  }});

  function zoomIn() {{ viewer.get('canvas').zoom(viewer.get('canvas').zoom() * 1.2); }}
  function zoomOut() {{ viewer.get('canvas').zoom(viewer.get('canvas').zoom() * 0.8); }}
  function fitView() {{ viewer.get('canvas').zoom('fit-viewport', 'auto'); }}
  function resetZoom() {{ viewer.get('canvas').zoom(1); viewer.get('canvas').scroll({{dx: 0, dy: 0}}); }}
</script>
</body>
</html>
"""
    return html


def main():
    st.title("CRM Process Optimizer")
    st.caption("Загрузите данные CRM и получите оптимизированную BPMN-схему и Use Case от AI")

    client = get_openai_client()
    demo_mode = client is None

    if demo_mode:
        st.info(
            "Работает в **демо-режиме** — OpenAI API Key не найден. "
            "Результаты будут сгенерированы на основе типового шаблона. "
            "Для персонализированного анализа добавьте `OPENAI_API_KEY` в переменные окружения.",
            icon="ℹ️",
        )

    with st.sidebar:
        st.header("Входные данные")

        uploaded_file = st.file_uploader(
            "Загрузить CRM-данные",
            type=["csv", "xlsx", "xls"],
            help="Поддерживаются файлы .csv и .xlsx/.xls",
        )

        df = None
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.success(f"Файл загружен: {len(df)} строк, {len(df.columns)} колонок")
                with st.expander("Предпросмотр данных"):
                    st.dataframe(df.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка чтения файла: {e}")
                df = None

        st.divider()

        problem_text = st.text_area(
            "Описание проблемы",
            placeholder="Например: Сделки зависают на этапе ТЗ, менеджеры долго отвечают. Конверсия падает, много лидов теряется.",
            height=160,
            help="Опишите текущую проблему в CRM-процессе",
        )

        st.divider()

        analyze_btn = st.button(
            "Сгенерировать процесс To-Be",
            type="primary",
            use_container_width=True,
            disabled=(df is None and not problem_text.strip() and not demo_mode),
        )

    if "bpmn_xml" not in st.session_state:
        st.session_state.bpmn_xml = None
    if "use_case_text" not in st.session_state:
        st.session_state.use_case_text = None
    if "generated" not in st.session_state:
        st.session_state.generated = False

    if analyze_btn or (demo_mode and st.button("Показать демо-результат", use_container_width=True) if False else False):
        if analyze_btn:
            with st.spinner("Анализируем данные и генерируем процесс..."):
                if demo_mode:
                    st.session_state.bpmn_xml = MOCK_BPMN
                    st.session_state.use_case_text = MOCK_USE_CASE.format(
                        date=datetime.now().strftime("%d.%m.%Y")
                    )
                    st.session_state.generated = True
                else:
                    try:
                        bpmn_xml, use_case_text = call_openai(client, df, problem_text)
                        if not bpmn_xml:
                            st.error("AI не вернул BPMN XML. Попробуйте ещё раз.")
                        else:
                            st.session_state.bpmn_xml = bpmn_xml
                            st.session_state.use_case_text = use_case_text
                            st.session_state.generated = True
                    except Exception as e:
                        st.error(f"Ошибка генерации: {e}")

    if st.session_state.generated and st.session_state.bpmn_xml:
        st.divider()
        tab1, tab2 = st.tabs(["Интерактивная BPMN-схема", "Use Cases / ТЗ"])

        with tab1:
            col1, col2 = st.columns([6, 1])
            with col1:
                st.subheader("Схема процесса To-Be")
            with col2:
                st.download_button(
                    label="Скачать .bpmn",
                    data=st.session_state.bpmn_xml.encode("utf-8"),
                    file_name="crm_process_to_be.bpmn",
                    mime="application/xml",
                    use_container_width=True,
                )

            from streamlit.components.v1 import html as st_html
            st_html(
                render_bpmn_viewer(st.session_state.bpmn_xml),
                height=620,
                scrolling=False,
            )

            if demo_mode:
                st.caption("Демо-схема. Загрузите данные и добавьте API Key для генерации персонализированной схемы.")

        with tab2:
            col1, col2 = st.columns([6, 1])
            with col1:
                st.subheader("Use Case / Техническое задание")
            with col2:
                if st.session_state.use_case_text:
                    st.download_button(
                        label="Скачать .md",
                        data=st.session_state.use_case_text.encode("utf-8"),
                        file_name="crm_use_case.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

            if st.session_state.use_case_text:
                st.markdown(st.session_state.use_case_text)
            else:
                st.info("Use Case не был сгенерирован.")

    elif not st.session_state.generated:
        st.markdown("### Как использовать")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**1. Загрузите данные**\n\nЗагрузите CSV или Excel-файл с данными CRM (выгрузка сделок, воронка, этапы)")
        with col2:
            st.info("**2. Опишите проблему**\n\nОпишите текущие узкие места в процессе — задержки, потери лидов, ошибки")
        with col3:
            st.info("**3. Получите результат**\n\nAI сгенерирует интерактивную BPMN-схему и структурированное ТЗ")

        st.markdown("---")
        st.markdown(
            "**Поддерживаемые форматы данных:** `.csv`, `.xlsx`, `.xls`  \n"
            "**AI-модель:** GPT-4o (требуется OpenAI API Key)  \n"
            "**Без ключа:** демо-режим с типовым шаблоном процесса"
        )


if __name__ == "__main__":
    main()
