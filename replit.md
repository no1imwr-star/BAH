# CRM Process Optimizer

A Streamlit web app that analyzes CRM data and generates optimized "To-Be" BPMN 2.0 process diagrams and structured Use Case documents using OpenAI GPT-4o.

## Run & Operate

- `cd artifacts/crm-optimizer && streamlit run app.py --server.port 5000` — run the app
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- Required env: `OPENAI_API_KEY` — OpenAI API key (optional; app runs in demo mode without it)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **App:** Python 3.11 + Streamlit 1.x
- **Data:** pandas, openpyxl, xlrd
- **AI:** OpenAI GPT-4o via `openai>=1.0.0`
- **BPMN rendering:** bpmn-js 17 via `streamlit.components.v1.html`
- API: Express 5
- DB: PostgreSQL + Drizzle ORM (not used by the Streamlit app)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/crm-optimizer/app.py` — main Streamlit application (all logic in one file)
- `artifacts/crm-optimizer/.streamlit/config.toml` — Streamlit server config (port 5000)
- `artifacts/crm-optimizer/requirements.txt` — Python dependencies for Render.com deploy
- `artifacts/crm-optimizer/runtime.txt` — Python version pin (`python-3.11.0`) for Render.com
- `artifacts/api-server/src/` — Express API server (separate service)

## Architecture decisions

- **Demo mode:** When `OPENAI_API_KEY` is absent, the app renders a built-in BPMN template and Use Case so users can evaluate the UI without credentials.
- **JSON response format:** OpenAI is called with `response_format={"type": "json_object"}` to guarantee a parseable response containing both `bpmn_xml` and `use_case` keys in one request.
- **bpmn-js via HTML component:** BPMN rendering is done entirely client-side via CDN-loaded bpmn-js injected through `streamlit.components.v1.html`. No server-side BPMN processing needed.
- **Session state caching:** Generated BPMN and Use Case are stored in `st.session_state` so they survive Streamlit reruns without re-calling the API.

## Product

- Upload CRM data (CSV / Excel) and describe a process bottleneck in plain text
- AI analyzes column structure, funnel stages, and the problem description
- Generates an interactive BPMN 2.0 diagram (pan + zoom) with Manager and CRM-system pools
- Generates a Cockburn-style Use Case document with actors, steps, alternatives, and KPIs
- Download results as `.bpmn` and `.md` files

## User preferences

- Language: Russian UI and generated content
- Deployment target: Render.com (requirements.txt + runtime.txt included)

## Gotchas

- The Streamlit workflow runs from the `artifacts/crm-optimizer/` directory — always `cd` there first
- `st.rerun()` must be used instead of the deprecated `experimental_rerun()`
- bpmn-js backtick characters in the XML must be escaped in the JS template literal

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
