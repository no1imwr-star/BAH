import os
import re
from datetime import datetime
from io import BytesIO
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from groq import Groq

app = FastAPI(title="BAlance.ai — AI Business Analyst Autopilot")

_TMPL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates  = Jinja2Templates(directory=_TMPL_DIR)
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
            raise RuntimeError("GROQ_API_KEY не найден в переменных окружения")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Ты — Lead Business Analyst с 15-летним опытом в крупных IT-проектах. \
Твоя задача — превратить краткую бизнес-идею или задачу пользователя \
в исчерпывающий пакет проектной документации. \
Выдай ответ строго на русском языке в формате Markdown. \
Разделяй блоки СТРОГО специальными маркерами, как указано ниже. \
НЕ добавляй лишнего текста между маркерами и контентом. \
Используй профессиональный, конкретный язык. Избегай воды и общих фраз.

Структура ответа:

[SECTION_VISION]
## Концепция и Границы проекта (Vision & Scope)

### Бизнес-цели
_Перечисли 3–5 конкретных бизнес-целей с измеримыми KPI._
- **Цель 1:** … | **KPI:** …
- **Цель 2:** … | **KPI:** …

### Границы проекта

**Входит в рамки разработки:**
- …

**НЕ входит в рамки (Out of Scope):**
- …

### Глоссарий проекта
| Термин | Определение |
|---|---|
| … | … |

[SECTION_SRS]
## Спецификация требований (SRS)

### Функциональные требования
_Нумерованный список конкретных требований к функциям системы._
1. **FR-01 [Название]:** …
2. **FR-02 [Название]:** …

### Нефункциональные требования
| Категория | Требование | Метрика |
|---|---|---|
| Производительность | … | … |
| Безопасность | … | … |
| UI/UX | … | … |
| Надёжность | … | … |

[SECTION_USECASES]
## Сценарии взаимодействия (Use Cases & User Stories)

### Роли и Акторы
| Актор | Роль в системе |
|---|---|
| … | … |

### Развёрнутый Use Case (Кокберн)
**Название:** …
**Актор:** …
**Предусловия:** …
**Основной сценарий:**
1. …
2. …
**Расширения (альтернативы/ошибки):**
- 3a. …
**Постусловия:** …

### User Stories для разработчиков
- [ ] **US-01:** Как [Роль], я хочу [Функционал], чтобы [Ценность].
- [ ] **US-02:** Как [Роль], я хочу [Функционал], чтобы [Ценность].

[SECTION_RTM]
## Матрица трассировки требований (RTM / MoSCoW)

| ID | Требование | Тип | Приоритет MoSCoW | Связанный Use Case | Статус |
|---|---|---|---|---|---|
| FR-01 | … | Функц. | Must Have | UC-01 | К разработке |
| FR-02 | … | Функц. | Should Have | UC-02 | К разработке |
| NFR-01 | … | Нефункц. | Must Have | — | К разработке |
"""

_USER_MSG_TEMPLATE = """\
Бизнес-задача / идея проекта:

{task}

Сгенерируй полный комплект проектной документации согласно инструкции. \
Будь конкретным и детальным — это реальный рабочий документ для команды разработки.
"""


# ---------------------------------------------------------------------------
# AI CALL
# ---------------------------------------------------------------------------
_SECTIONS = ["VISION", "SRS", "USECASES", "RTM"]

def _parse_sections(text: str) -> dict[str, str]:
    """Split AI response into named sections by [SECTION_XXX] markers."""
    result: dict[str, str] = {}
    pattern = r"\[SECTION_(" + "|".join(_SECTIONS) + r")\]"
    parts = re.split(pattern, text)
    # parts = [pre, NAME, content, NAME, content, ...]
    i = 1
    while i < len(parts) - 1:
        name    = parts[i].strip()
        content = parts[i + 1].strip()
        result[name] = content
        i += 2
    return result


def call_ai(task: str) -> dict:
    """Call Groq and return parsed sections + full markdown."""
    client = _get_groq()
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": _USER_MSG_TEMPLATE.format(task=task)},
        ],
        temperature=0.4,
        max_tokens=4096,
    )
    raw = completion.choices[0].message.content or ""
    sections = _parse_sections(raw)
    full_md  = raw
    return {"sections": sections, "full_md": full_md}


# ---------------------------------------------------------------------------
# DEMO CONTENT (no API key)
# ---------------------------------------------------------------------------
_DEMO_SECTIONS = {
    "VISION": """\
## Концепция и Границы проекта (Vision & Scope)

### Бизнес-цели
- **Цель 1:** Автоматизировать складской учёт | **KPI:** Сократить время инвентаризации на 70% за 6 месяцев
- **Цель 2:** Исключить ручные ошибки при приёмке | **KPI:** 0 расхождений в отчётах ≥ 99% операций
- **Цель 3:** Ускорить отгрузку товара | **KPI:** Среднее время отгрузки ≤ 15 минут

### Границы проекта

**Входит в рамки разработки:**
- Учёт остатков на складе в реальном времени
- Приёмка и отгрузка товаров с QR/штрих-кодами
- Отчёты по движению товаров (ежедневные / ежемесячные)
- Роли пользователей: кладовщик, менеджер, директор

**НЕ входит в рамки (Out of Scope):**
- Интеграция с 1С (следующая фаза)
- Мобильное приложение (следующая фаза)
- Управление поставщиками и закупками

### Глоссарий проекта
| Термин | Определение |
|---|---|
| SKU | Артикул складской единицы учёта |
| Инвентаризация | Физический подсчёт остатков на складе |
| Отгрузка | Передача товара клиенту со склада |
| Приёмка | Принятие товара от поставщика на склад |
""",
    "SRS": """\
## Спецификация требований (SRS)

### Функциональные требования
1. **FR-01 [Авторизация]:** Система должна поддерживать вход по логину и паролю с разграничением прав по ролям.
2. **FR-02 [Учёт остатков]:** Система должна отображать актуальные остатки по каждому SKU в режиме реального времени.
3. **FR-03 [Приёмка]:** Кладовщик должен иметь возможность принять товар с автоматическим обновлением остатков.
4. **FR-04 [Отгрузка]:** Система должна фиксировать отгрузку и уменьшать остаток, создавая накладную.
5. **FR-05 [Отчёты]:** Менеджер должен иметь доступ к отчётам о движении товаров за произвольный период.

### Нефункциональные требования
| Категория | Требование | Метрика |
|---|---|---|
| Производительность | Загрузка любой страницы | ≤ 2 сек при 100 одновременных пользователях |
| Безопасность | Шифрование паролей | bcrypt, соль ≥ 10 раундов |
| UI/UX | Минимальное обучение | Новый кладовщик должен освоить систему за 30 минут |
| Надёжность | Доступность сервиса | 99.5% uptime в рабочее время |
""",
    "USECASES": """\
## Сценарии взаимодействия (Use Cases & User Stories)

### Роли и Акторы
| Актор | Роль в системе |
|---|---|
| Кладовщик | Осуществляет приёмку и отгрузку товаров |
| Менеджер | Просматривает отчёты и управляет номенклатурой |
| Директор | Доступ к сводным аналитическим отчётам |
| Система | Автоматически обновляет остатки и отправляет уведомления |

### Развёрнутый Use Case (Кокберн)
**Название:** UC-01 Приёмка товара на склад
**Актор:** Кладовщик
**Предусловия:** Кладовщик авторизован; у поставщика есть накладная
**Основной сценарий:**
1. Кладовщик открывает раздел «Приёмка».
2. Сканирует QR-код или вводит номер накладной.
3. Система отображает список товаров из накладной.
4. Кладовщик сканирует каждую единицу и подтверждает количество.
5. Система обновляет остатки и создаёт электронную приходную накладную.
**Расширения:**
- 4a. Количество не совпадает → система запрашивает подтверждение расхождения.
- 4b. SKU не найден → система предлагает создать новую позицию.
**Постусловия:** Остатки обновлены; приходная накладная сохранена в системе.

### User Stories для разработчиков
- [ ] **US-01:** Как кладовщик, я хочу сканировать штрих-код товара, чтобы автоматически обновлять остатки без ручного ввода.
- [ ] **US-02:** Как менеджер, я хочу выгружать отчёт за период в Excel, чтобы анализировать движение товаров.
- [ ] **US-03:** Как директор, я хочу видеть дашборд с ключевыми метриками склада, чтобы принимать оперативные решения.
- [ ] **US-04:** Как кладовщик, я хочу получать уведомление при достижении минимального остатка, чтобы своевременно заказывать товар.
""",
    "RTM": """\
## Матрица трассировки требований (RTM / MoSCoW)

| ID | Требование | Тип | Приоритет MoSCoW | Связанный Use Case | Статус |
|---|---|---|---|---|---|
| FR-01 | Авторизация по ролям | Функц. | Must Have | UC-00 | К разработке |
| FR-02 | Учёт остатков в реальном времени | Функц. | Must Have | UC-01 | К разработке |
| FR-03 | Приёмка товара | Функц. | Must Have | UC-01 | К разработке |
| FR-04 | Отгрузка и накладная | Функц. | Must Have | UC-02 | К разработке |
| FR-05 | Отчёты за период | Функц. | Should Have | UC-03 | К разработке |
| NFR-01 | Производительность ≤ 2 сек | Нефункц. | Must Have | — | К разработке |
| NFR-02 | Шифрование паролей bcrypt | Нефункц. | Must Have | — | К разработке |
| NFR-03 | Excel-экспорт отчётов | Функц. | Could Have | UC-03 | К разработке |
| NFR-04 | Мобильная версия | Функц. | Won't Have | — | Следующая фаза |
""",
}


# ---------------------------------------------------------------------------
# HTML HELPERS
# ---------------------------------------------------------------------------
def _read_html() -> str:
    with open(_HTML_FILE, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
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
        full_md = "\n\n".join(
            f"[SECTION_{k}]\n{v}" for k, v in _DEMO_SECTIONS.items()
        )
        return JSONResponse({
            "sections": _DEMO_SECTIONS,
            "full_md":  full_md,
            "demo":     True,
        })

    try:
        result = call_ai(task)
        # Fall back to demo if sections are mostly empty
        if len(result["sections"]) < 2:
            result["sections"] = _DEMO_SECTIONS
        result["demo"] = False
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# MARKDOWN → DOCX CONVERTER
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
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    lines = md_text.splitlines()
    i = 0
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
                p = cell.paragraphs[0]
                run = p.add_run(cell_text)
                if ri == 0:
                    run.bold = True
        table_rows.clear()
        doc.add_paragraph()

    while i < len(lines):
        raw = lines[i]
        s   = raw.strip()

        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^[\|\s\-:]+$", s):
                i += 1
                continue
            cells = [c.strip() for c in s[1:-1].split("|")]
            table_rows.append(cells)
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
            text = re.sub(r"^[-*] \[[ x]\] ", "☐ ", s)
            p = doc.add_paragraph(style="List Bullet")
            _bold_run(p, text)
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
# MARKDOWN → PDF CONVERTER  (ReportLab)
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
                bold_path = candidate.replace("Regular", "Bold")
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("UniFont-Bold", bold_path))
                    _FONT_BOLD = "UniFont-Bold"
                _FONT_NAME = "UniFont"
            except Exception:
                pass
            break

    accent = colors.HexColor("#FF385C")
    dark   = colors.HexColor("#222222")

    sty = {
        "h1":      ParagraphStyle("h1",      fontName=_FONT_BOLD, fontSize=16, textColor=dark,
                                  spaceAfter=8,  spaceBefore=14, leading=20),
        "h2":      ParagraphStyle("h2",      fontName=_FONT_BOLD, fontSize=12, textColor=accent,
                                  spaceAfter=5,  spaceBefore=12, leading=16),
        "h3":      ParagraphStyle("h3",      fontName=_FONT_BOLD, fontSize=10.5, textColor=dark,
                                  spaceAfter=4,  spaceBefore=8,  leading=14),
        "body":    ParagraphStyle("body",    fontName=_FONT_NAME, fontSize=10, textColor=dark,
                                  spaceAfter=4,  leading=14),
        "bullet":  ParagraphStyle("bullet",  fontName=_FONT_NAME, fontSize=10, textColor=dark,
                                  leftIndent=14, spaceAfter=2,   leading=13),
        "cell":    ParagraphStyle("cell",    fontName=_FONT_NAME, fontSize=8.5, textColor=dark,
                                  leading=11),
        "cell_hd": ParagraphStyle("cell_hd", fontName=_FONT_BOLD, fontSize=8.5,
                                  textColor=colors.white, leading=11),
    }

    def strip_inline(t: str) -> str:
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
        t = re.sub(r"\*(.+?)\*",   r"\1", t)
        t = re.sub(r"`([^`]+)`",   r"\1", t)
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
            row_cells = []
            for ci in range(n_cols):
                txt = row[ci] if ci < len(row) else ""
                st  = sty["cell_hd"] if ri == 0 else sty["cell"]
                row_cells.append(Paragraph(strip_inline(txt), st))
            tdata.append(row_cells)
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

        # Skip section markers
        if s.startswith("[SECTION_"):
            i += 1
            continue

        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^[\|\s\-:]+$", s):
                i += 1
                continue
            cells = [c.strip() for c in s[1:-1].split("|")]
            table_rows.append(cells)
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
            text = "☐ " + strip_inline(re.sub(r"^[-*] \[[ x]\] ", "", s))
            story.append(Paragraph(text, sty["bullet"]))
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
        return JSONResponse({"error": f"Ошибка генерации DOCX: {e}"}, status_code=500)
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
        return JSONResponse({"error": f"Ошибка генерации PDF: {e}"}, status_code=500)
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
