import os
import io
import json
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="CRM Process Optimizer", page_icon="⚙️", layout="wide")

# ---------------------------------------------------------------------------
# Groq — optional import, graceful fallback to demo mode
# ---------------------------------------------------------------------------
try:
    from groq import Groq as _Groq
    _GROQ_LIB = True
except Exception:
    _GROQ_LIB = False

# ---------------------------------------------------------------------------
# Demo-mode assets
# ---------------------------------------------------------------------------
MOCK_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_1">
  <collaboration id="Collaboration_1">
    <participant id="Pool_Manager" name="Менеджер по продажам" processRef="Process_Manager"/>
    <participant id="Pool_CRM"     name="CRM-система"          processRef="Process_CRM"/>
  </collaboration>

  <process id="Process_Manager" isExecutable="false">
    <startEvent id="SE1" name="Новая заявка"><outgoing>F1</outgoing></startEvent>
    <userTask   id="T1"  name="Квалификация лида"><incoming>F1</incoming><outgoing>F2</outgoing></userTask>
    <exclusiveGateway id="GW1" name="Квалифицирован?"><incoming>F2</incoming><outgoing>F3</outgoing><outgoing>F4</outgoing></exclusiveGateway>
    <userTask   id="T2"  name="Подготовить ТЗ"><incoming>F3</incoming><outgoing>F5</outgoing></userTask>
    <userTask   id="T3"  name="Презентация решения"><incoming>F5</incoming><outgoing>F6</outgoing></userTask>
    <userTask   id="T4"  name="Согласование КП"><incoming>F6</incoming><outgoing>F7</outgoing></userTask>
    <exclusiveGateway id="GW2" name="Сделка закрыта?"><incoming>F7</incoming><outgoing>F8</outgoing><outgoing>F9</outgoing></exclusiveGateway>
    <endEvent   id="EE1" name="Выиграна"><incoming>F8</incoming></endEvent>
    <endEvent   id="EE2" name="Проиграна"><incoming>F4</incoming></endEvent>
    <endEvent   id="EE3" name="Дозревание"><incoming>F9</incoming></endEvent>
    <sequenceFlow id="F1" sourceRef="SE1" targetRef="T1"/>
    <sequenceFlow id="F2" sourceRef="T1"  targetRef="GW1"/>
    <sequenceFlow id="F3" name="Да" sourceRef="GW1" targetRef="T2"/>
    <sequenceFlow id="F4" name="Нет" sourceRef="GW1" targetRef="EE2"/>
    <sequenceFlow id="F5" sourceRef="T2"  targetRef="T3"/>
    <sequenceFlow id="F6" sourceRef="T3"  targetRef="T4"/>
    <sequenceFlow id="F7" sourceRef="T4"  targetRef="GW2"/>
    <sequenceFlow id="F8" name="Да" sourceRef="GW2" targetRef="EE1"/>
    <sequenceFlow id="F9" name="Нет" sourceRef="GW2" targetRef="EE3"/>
  </process>

  <process id="Process_CRM" isExecutable="false">
    <startEvent  id="CS1" name="Регистрация заявки"><outgoing>CF1</outgoing></startEvent>
    <serviceTask id="CT1" name="Уведомить менеджера"><incoming>CF1</incoming><outgoing>CF2</outgoing></serviceTask>
    <serviceTask id="CT2" name="Рассчитать скоринг"><incoming>CF2</incoming><outgoing>CF3</outgoing></serviceTask>
    <serviceTask id="CT3" name="Обновить статус сделки"><incoming>CF3</incoming><outgoing>CF4</outgoing></serviceTask>
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
      <!-- Manager pool -->
      <bpmndi:BPMNShape id="Pool_Manager_di" bpmnElement="Pool_Manager" isHorizontal="true">
        <dc:Bounds x="130" y="60" width="950" height="200"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="SE1_di" bpmnElement="SE1">
        <dc:Bounds x="182" y="142" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="155" y="185" width="90" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T1_di" bpmnElement="T1">
        <dc:Bounds x="268" y="120" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW1_di" bpmnElement="GW1" isMarkerVisible="true">
        <dc:Bounds x="418" y="135" width="50" height="50"/>
        <bpmndi:BPMNLabel><dc:Bounds x="400" y="192" width="86" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T2_di" bpmnElement="T2">
        <dc:Bounds x="518" y="120" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T3_di" bpmnElement="T3">
        <dc:Bounds x="668" y="120" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="T4_di" bpmnElement="T4">
        <dc:Bounds x="818" y="120" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW2_di" bpmnElement="GW2" isMarkerVisible="true">
        <dc:Bounds x="968" y="135" width="50" height="50"/>
        <bpmndi:BPMNLabel><dc:Bounds x="950" y="192" width="86" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE1_di" bpmnElement="EE1">
        <dc:Bounds x="1040" y="142" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="1022" y="185" width="72" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE2_di" bpmnElement="EE2">
        <dc:Bounds x="425" y="72" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="407" y="55" width="72" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EE3_di" bpmnElement="EE3">
        <dc:Bounds x="975" y="72" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="957" y="55" width="72" height="14"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="F1_di"  bpmnElement="F1"><di:waypoint x="218" y="160"/><di:waypoint x="268" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F2_di"  bpmnElement="F2"><di:waypoint x="368" y="160"/><di:waypoint x="418" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F3_di"  bpmnElement="F3"><di:waypoint x="468" y="160"/><di:waypoint x="518" y="160"/><bpmndi:BPMNLabel><dc:Bounds x="487" y="142" width="13" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F4_di"  bpmnElement="F4"><di:waypoint x="443" y="135"/><di:waypoint x="443" y="108"/><bpmndi:BPMNLabel><dc:Bounds x="450" y="118" width="22" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F5_di"  bpmnElement="F5"><di:waypoint x="618" y="160"/><di:waypoint x="668" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F6_di"  bpmnElement="F6"><di:waypoint x="768" y="160"/><di:waypoint x="818" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F7_di"  bpmnElement="F7"><di:waypoint x="918" y="160"/><di:waypoint x="968" y="160"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F8_di"  bpmnElement="F8"><di:waypoint x="1018" y="160"/><di:waypoint x="1040" y="160"/><bpmndi:BPMNLabel><dc:Bounds x="1022" y="142" width="13" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="F9_di"  bpmnElement="F9"><di:waypoint x="993" y="135"/><di:waypoint x="993" y="108"/><bpmndi:BPMNLabel><dc:Bounds x="1000" y="118" width="22" height="14"/></bpmndi:BPMNLabel></bpmndi:BPMNEdge>

      <!-- CRM pool -->
      <bpmndi:BPMNShape id="Pool_CRM_di" bpmnElement="Pool_CRM" isHorizontal="true">
        <dc:Bounds x="130" y="290" width="950" height="180"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CS1_di" bpmnElement="CS1">
        <dc:Bounds x="182" y="362" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="155" y="405" width="90" height="27"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT1_di" bpmnElement="CT1">
        <dc:Bounds x="268" y="340" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT2_di" bpmnElement="CT2">
        <dc:Bounds x="418" y="340" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT3_di" bpmnElement="CT3">
        <dc:Bounds x="568" y="340" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CT4_di" bpmnElement="CT4">
        <dc:Bounds x="718" y="340" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="CE1_di" bpmnElement="CE1">
        <dc:Bounds x="870" y="362" width="36" height="36"/>
        <bpmndi:BPMNLabel><dc:Bounds x="843" y="405" width="90" height="27"/></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="CF1_di" bpmnElement="CF1"><di:waypoint x="218" y="380"/><di:waypoint x="268" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF2_di" bpmnElement="CF2"><di:waypoint x="368" y="380"/><di:waypoint x="418" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF3_di" bpmnElement="CF3"><di:waypoint x="518" y="380"/><di:waypoint x="568" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF4_di" bpmnElement="CF4"><di:waypoint x="668" y="380"/><di:waypoint x="718" y="380"/></bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="CF5_di" bpmnElement="CF5"><di:waypoint x="818" y="380"/><di:waypoint x="870" y="380"/></bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""

MOCK_USE_CASE = """# Use Case: Оптимизированный процесс работы с CRM (To-Be)

---

## UC-001 — Полный цикл обработки лида

**Версия:** 1.0 | **Дата:** {date} | **Статус:** Черновик (Demo Mode)

---

### 1. Акторы

| Актор | Тип | Описание |
|-------|-----|----------|
| Менеджер по продажам | Основной | Квалифицирует лид, ведёт переговоры, закрывает сделку |
| CRM-система | Вторичный | Регистрирует заявки, рассчитывает скоринг, обновляет статусы |
| Руководитель отдела | Вторичный | Мониторит воронку и получает эскалации |

### 2. Предусловия
- Новая заявка поступила из любого канала (сайт, звонок, реферал)
- Менеджер авторизован в CRM-системе

### 3. Основной сценарий

| Шаг | Актор | Действие | Результат |
|-----|-------|----------|-----------|
| 1 | CRM | Автоматически регистрирует заявку, присваивает ID | Лид создан |
| 2 | CRM | Рассчитывает скоринг лида | Скоринговая оценка присвоена |
| 3 | CRM | Уведомляет ответственного менеджера (push + email) | Менеджер получает уведомление |
| 4 | Менеджер | Открывает карточку, изучает скоринг | Принято решение о квалификации |
| 5 | Менеджер | Проводит первичный контакт, оценивает ICP | Лид квалифицирован как целевой |
| 6 | Менеджер | Переводит лид в статус «В работе» | Статус обновлён в CRM |
| 7 | Менеджер | Готовит и согласовывает ТЗ с клиентом | ТЗ утверждено |
| 8 | Менеджер | Проводит презентацию решения | Клиент заинтересован |
| 9 | Менеджер | Формирует и отправляет КП | КП выслано клиенту |
| 10 | Менеджер | Фиксирует результат сделки в CRM | Сделка закрыта как «Выиграна» |
| 11 | CRM | Генерирует итоговый отчёт | Данные актуализированы |

### 4. Альтернативные сценарии

**4.1 Лид не прошёл квалификацию (шаг 5)**
- Менеджер переводит лид в статус «Нецелевой» с указанием причины
- CRM архивирует лид; при необходимости ставится задача повторного контакта через 3 месяца

**4.2 Клиент не готов к покупке (шаг 9)**
- Менеджер переводит лид в статус «Дозревание», устанавливает дату следующего контакта
- CRM создаёт напоминание; лид остаётся в воронке с пониженным приоритетом

**4.3 Сбой CRM**
- Менеджер фиксирует данные резервно; системный администратор получает алерт
- После восстановления данные переносятся; инцидент логируется

### 5. Постусловия
- Сделка имеет финальный статус: «Выиграна», «Проиграна» или «Дозревание»
- Все взаимодействия с клиентом зафиксированы в истории лида
- KPI менеджера обновлены автоматически

### 6. Бизнес-правила

| Код | Правило |
|-----|---------|
| BR-01 | SLA первого контакта — не более **2 часов** с момента поступления заявки |
| BR-02 | ТЗ согласовывается не позднее **5 рабочих дней** с начала переговоров |
| BR-03 | КП направляется клиенту в течение **24 часов** после утверждения ТЗ |
| BR-04 | Лид без активности более **14 дней** автоматически эскалируется руководителю |

### 7. Метрики успеха

| Метрика | As-Is | To-Be |
|---------|-------|-------|
| Время первого контакта | > 4 ч | < 2 ч |
| Конверсия лид → сделка | ~15% | > 25% |
| Среднее время на этапе ТЗ | 7–10 дней | 3–5 дней |
| Потеря лидов из-за задержек | ~20% | < 5% |

---
*Сгенерировано CRM Process Optimizer в демо-режиме. Загрузите данные и добавьте OPENAI\\_API\\_KEY для персонализированного анализа.*
"""


# ---------------------------------------------------------------------------
# Groq client — returns None if key absent or lib not installed
# ---------------------------------------------------------------------------
def get_groq_client():
    try:
        if not _GROQ_LIB:
            return None
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            try:
                api_key = st.secrets.get("GROQ_API_KEY")
            except Exception:
                pass
        if api_key:
            return _Groq(api_key=api_key)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ты — Lead BA (BABOK v3, BPMN 2.0, Коберн). Ответ строго JSON без markdown-блоков.
Формат: {"bpmn_xml": "...", "use_case": "..."}

BPMN XML: валидный BPMN 2.0 для bpmn-js v17. Два пула: "Менеджер по продажам" и "CRM-система". Полная BPMNDiagram (BPMNShape/BPMNEdge с координатами). Уникальные id. НЕ backtick внутри XML. Минимум 5 элементов в каждом пуле.

Use Case (Коберн): бизнес-стиль, без воды. Обязательно: акторы (таблица), предусловия (список), основной сценарий (таблица Шаг|Актор|Действие|Результат), альтернативы и edge cases (ошибки API, таймауты, роли), бизнес-правила (Код|Правило|SLA), метрики As-Is vs To-Be (таблица). Markdown с таблицами, H2/H3.
"""


def build_user_prompt(df, problem_text):
    cols_info = ""
    if df is not None:
        sample = df.head(3).to_string()
        cols_info = (
            f"Данные CRM:\n- Строк: {len(df)}\n"
            f"- Колонки: {', '.join(df.columns.tolist())}\n"
            f"- Примеры:\n{sample}\n"
        )
    problem = problem_text.strip() if problem_text else "Не указано — создай типовой оптимизированный процесс."
    return (
        f"{cols_info}\nПроблема / задача:\n{problem}\n\n"
        'Ответь строго JSON без markdown: {"bpmn_xml": "...", "use_case": "..."}'
    )


def call_groq(client, df, problem_text):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(df, problem_text)},
        ],
        temperature=0.3,
        max_tokens=6000,
    )
    raw = response.choices[0].message.content or ""
    # Strip accidental markdown code fences
    import re
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())
    data = json.loads(raw)
    return data.get("bpmn_xml", ""), data.get("use_case", "")


# ---------------------------------------------------------------------------
# BPMN viewer — escape order: backslashes first, then backticks, then $
# ---------------------------------------------------------------------------
def render_bpmn_html(bpmn_xml: str) -> str:
    safe = bpmn_xml.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:100%;height:100%;background:#f8f9fa}}
  #canvas{{width:100%;height:570px;background:#fff;border:1px solid #dee2e6;border-radius:6px}}
  #ctrl{{position:absolute;top:8px;right:8px;z-index:10;display:flex;gap:4px}}
  .btn{{padding:5px 11px;background:#fff;border:1px solid #ced4da;border-radius:4px;
        cursor:pointer;font-size:13px;font-family:sans-serif;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
  .btn:hover{{background:#f1f3f5}}
  #err{{display:none;margin:8px;padding:10px 14px;background:#fff3cd;
        border:1px solid #ffc107;border-radius:6px;font-family:sans-serif;font-size:13px;color:#856404}}
  #wrap{{position:relative;width:100%}}
</style>
</head>
<body>
<div id="wrap">
  <div id="ctrl">
    <button class="btn" onclick="zi()">＋</button>
    <button class="btn" onclick="zo()">－</button>
    <button class="btn" onclick="fv()">По размеру</button>
    <button class="btn" onclick="rz()">1:1</button>
  </div>
  <div id="err"></div>
  <div id="canvas"></div>
</div>
<script src="https://unpkg.com/bpmn-js@17.2.1/dist/bpmn-viewer.development.js"></script>
<script>
var xml=`{safe}`;
var v=new BpmnJS({{container:'#canvas'}});
v.importXML(xml).then(function(){{
  v.get('canvas').zoom('fit-viewport','auto');
}}).catch(function(e){{
  var d=document.getElementById('err');
  d.style.display='block';
  d.textContent='Ошибка рендеринга BPMN: '+e.message;
}});
function zi(){{v.get('canvas').zoom(v.get('canvas').zoom()*1.2)}}
function zo(){{v.get('canvas').zoom(v.get('canvas').zoom()*0.8)}}
function fv(){{v.get('canvas').zoom('fit-viewport','auto')}}
function rz(){{v.get('canvas').zoom(1)}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main():
    st.title("⚙️ CRM Process Optimizer")
    st.caption("Загрузите данные CRM → опишите проблему → получите BPMN-схему и Use Case от AI")

    client = get_groq_client()
    demo_mode = client is None

    if demo_mode:
        st.info(
            "**Демо-режим:** GROQ_API_KEY не найден. "
            "Показан типовой шаблон. Добавьте ключ в переменные окружения для персонализированного анализа.",
            icon="ℹ️",
        )

    # --- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.header("Входные данные")

        uploaded = st.file_uploader(
            "CRM-данные (.csv / .xlsx / .xls)",
            type=["csv", "xlsx", "xls"],
        )

        df = None
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
                st.success(f"Загружено: {len(df)} строк, {len(df.columns)} колонок")
                with st.expander("Предпросмотр"):
                    st.dataframe(df.head(8), use_container_width=True)
            except Exception as exc:
                st.error(f"Ошибка чтения файла: {exc}")

        st.divider()
        problem = st.text_area(
            "Описание проблемы",
            placeholder="Например: Сделки зависают на этапе ТЗ, менеджеры долго отвечают. Конверсия падает.",
            height=140,
        )
        st.divider()
        run_btn = st.button("🚀 Сгенерировать процесс To-Be", type="primary", use_container_width=True)

    # --- Session state -----------------------------------------------------
    if "bpmn_xml" not in st.session_state:
        st.session_state.bpmn_xml = None
    if "use_case" not in st.session_state:
        st.session_state.use_case = None

    # --- Generation --------------------------------------------------------
    if run_btn:
        with st.spinner("Анализируем данные и генерируем процесс…"):
            if demo_mode:
                st.session_state.bpmn_xml = MOCK_BPMN
                st.session_state.use_case = MOCK_USE_CASE.format(date=datetime.now().strftime("%d.%m.%Y"))
            else:
                try:
                    bxml, uc = call_groq(client, df, problem)
                    if not bxml:
                        st.error("AI не вернул BPMN XML. Попробуйте ещё раз.")
                    else:
                        st.session_state.bpmn_xml = bxml
                        st.session_state.use_case = uc
                except Exception as exc:
                    st.error(f"Ошибка обращения к Groq: {exc}")

    # --- Results -----------------------------------------------------------
    if st.session_state.bpmn_xml:
        st.divider()
        tab1, tab2 = st.tabs(["📊 Интерактивная BPMN-схема", "📄 Use Cases / ТЗ"])

        with tab1:
            c1, c2 = st.columns([8, 2])
            c1.subheader("Схема процесса To-Be")
            c2.download_button(
                "⬇ Скачать .bpmn",
                data=st.session_state.bpmn_xml.encode("utf-8"),
                file_name="crm_to_be.bpmn",
                mime="application/xml",
                use_container_width=True,
            )
            import streamlit.components.v1 as components
            components.html(render_bpmn_html(st.session_state.bpmn_xml), height=600, scrolling=False)
            if demo_mode:
                st.caption("Демо-схема. Добавьте API Key для персонализированной генерации.")

        with tab2:
            c1, c2 = st.columns([8, 2])
            c1.subheader("Use Case / Техническое задание")
            if st.session_state.use_case:
                c2.download_button(
                    "⬇ Скачать .md",
                    data=st.session_state.use_case.encode("utf-8"),
                    file_name="crm_use_case.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                st.markdown(st.session_state.use_case)

    else:
        # Landing instructions
        st.markdown("### Как использовать")
        col1, col2, col3 = st.columns(3)
        col1.info("**1. Загрузите данные**\n\nCSV или Excel-файл с выгрузкой сделок / воронкой CRM")
        col2.info("**2. Опишите проблему**\n\nЗадержки, потери лидов, узкие места — своими словами")
        col3.info("**3. Получите результат**\n\nBPMN-схема с двумя пулами и структурированное ТЗ")
        st.markdown(
            "---\n"
            "**Форматы:** `.csv`, `.xlsx`, `.xls` &nbsp;·&nbsp; "
            "**AI:** Groq · llama-3.3-70b &nbsp;·&nbsp; "
            "**Без ключа:** демо-режим с готовым шаблоном"
        )


if __name__ == "__main__":
    main()
