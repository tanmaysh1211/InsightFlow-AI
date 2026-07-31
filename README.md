# InsightFlow-AI

An enterprise-grade, multi-agent AI platform for natural language business analytics. The system generates safe SQL queries, executes them against relational databases, selects appropriate visualization structures, detects statistical anomalies, and recommends business strategies with comprehensive observability logging.

Think of it as Microsoft's Power BI Copilot or Tableau AI, built from the ground up with modular, asynchronous agent orchestration.

---

## 🌟 Key Features

- **Multi-Agent Coordination**: Asynchronous coordination across specialized nodes:
  - **Planner Agent**: Parses user intent and prepares the execution pipeline.
  - **Schema Agent**: Isolates tables to avoid token pollution.
  - **SQL Agent**: Generates dialet-appropriate SELECT statements.
  - **Validator Agent**: Screens queries against destructive actions (`DROP`, `DELETE`, `UPDATE`, `ALTER`).
  - **Visualizer Agent**: Configures standard charts matching query outputs.
  - **Analytics Agent**: Extracts growth metrics and highlights anomaly outlines.
  - **Recommender Agent**: Recommends strategic actionable items.
  - **Report Agent**: Generates structured executive markdown briefings.
- **Dynamic Data linking**: Connect to PostgreSQL, MySQL, SQL Server, or SQLite from the UI.
- **Dual Mode Architecture**:
  - _Simulation Mode_: Operational out of the box using deterministic keyword engines (no LLM keys required).
  - _LLM Live Mode_: Routes requests to OPENAI (Llama 3.3) or OpenRouter (Gemini 2.5 Flash / Qwen 2.5).
- **Observability Dashboard**: Audit latency, token consumption, query cost estimates, and traceback logs for every single agent invocation.

---

## 🛠️ Technology Stack

- **Frontend (100% Python)**: Streamlit, Plotly, Pandas, httpx.
- **Backend**: Python, FastAPI, SQLAlchemy, Async architecture (aiosqlite), Pydantic, Cryptography.
- **Ops & Deployment**: Docker, Docker Compose.

---

## 🚀 Quick Start (Local Setup)

### Prerequisites

- Python 3.10+ (Fully compatible with Python 3.13)

### 1. Initialize Mock Database

Set up the `enterprise_demo.db` SQLite database (contains sample tables: `customers`, `products`, `orders`, `payments`, `inventory`):

```bash
python setup_demo_db.py
```

### 2. Start Backend API

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will run at `http://localhost:8000`.

### 3. Start Streamlit Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

The Streamlit dashboard will run at `http://localhost:8501`.

### 4. Docker Compose Deployment

Alternatively, build and start both Python containers:

```bash
docker-compose up --build
```

---

## 🔬 Observability & Telemetry

Every agent executes under a common BaseAgent class, generating telemetry payloads recorded on the `copilot_metadata.db` store:

- **Execution Time**: Precise latency counters.
- **Calculated Cost**: Token calculations based on model cost ratios.
- **Logs**: Audit traces, dialet queries, and processing warnings visible in the **Agent Logs** workspace.
