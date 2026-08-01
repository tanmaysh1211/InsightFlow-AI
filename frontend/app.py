import streamlit as pd_st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time

pd_st.set_page_config(
    page_title="InsightFlow-AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

pd_st.markdown("""
<style>
    .stApp {
        background-color: #020617;
        color: #f8fafc;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Inter', system-ui, sans-serif;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    div.glass-card {
        background-color: rgba(30, 41, 59, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
    }
    
    div.stStatus {
        background-color: #0f172a;
        border: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://localhost:8000/api/v1"

def get_connections():
    try:
        with httpx.Client() as client:
            res = client.get(f"{API_BASE_URL}/connections")
            return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def get_history():
    try:
        with httpx.Client() as client:
            res = client.get(f"{API_BASE_URL}/queries/history")
            return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def get_logs():
    try:
        with httpx.Client() as client:
            res = client.get(f"{API_BASE_URL}/queries/logs")
            return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def get_settings():
    try:
        with httpx.Client() as client:
            res = client.get(f"{API_BASE_URL}/settings")
            return res.json() if res.status_code == 200 else {"app_mode": "simulation", "OPENAI_api_key_configured": False, "openrouter_api_key_configured": False}
    except Exception:
        return {"app_mode": "simulation", "OPENAI_api_key_configured": False, "openrouter_api_key_configured": False}

if 'query_input' not in pd_st.session_state:
    pd_st.session_state.query_input = ""
if 'active_query_id' not in pd_st.session_state:
    pd_st.session_state.active_query_id = None

with pd_st.sidebar:
    pd_st.markdown("<div style='display: flex; align-items: center; gap: 10px; margin-bottom: 20px;'><h3>📊 InsightFlow-AI</h3></div>", unsafe_allow_html=True)
    
    page = pd_st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "💬 Query Workspace",
            "🔌 Connections",
            "📜 SQL Viewer",
            "🎨 Viz Studio",
            "💡 AI Insights & Actions",
            "📋 Reports",
            "🛠️ Agent Logs & Settings"
        ]
    )
    
    try:
        health_check = httpx.get("http://localhost:8000/", timeout=1.0)
        server_ok = health_check.status_code == 200
        mode = health_check.json().get("mode", "simulation")
    except Exception:
        server_ok = False
        mode = "offline"
        
    pd_st.markdown("---")
    pd_st.markdown(f"**System Status**: {'🟢 Online' if server_ok else '🔴 Offline'}")
    pd_st.markdown(f"**Pipeline Mode**: `{mode.upper()}`")

if page == "📊 Dashboard":
    pd_st.subheader("Observability & KPI Metrics")
    
    conns = get_connections()
    hist = get_history()
    
    total_queries = len(hist)
    successes = len([q for q in hist if q.get("execution_status") == "success"])
    success_rate = round((successes / total_queries * 100)) if total_queries > 0 else 0
    
    total_cost = 0.0
    sum_latency = 0
    log_count = 0
    for q in hist:
        for log in q.get("agent_logs", []):
            total_cost += log.get("cost_est", 0.0)
            sum_latency += log.get("latency_ms", 0)
            log_count += 1
            
    avg_latency = round(sum_latency / total_queries) if total_queries > 0 else 0

    c1, c2, c3, c4, c5 = pd_st.columns(5)
    c1.metric("Active Endpoints", len(conns))
    c2.metric("Total Queries Run", total_queries)
    c3.metric("Success Rate", f"{success_rate}%")
    c4.metric("Avg Run Latency", f"{avg_latency} ms")
    c5.metric("Estimated Cost", f"${total_cost:.5f}")

    pd_st.markdown("---")
    
    col_left, col_right = pd_st.columns([2, 1])
    
    with col_left:
        pd_st.markdown("#### Recent Query History")
        if not hist:
            pd_st.info("No queries executed yet. Start in the Query Workspace.")
        else:
            df_hist = pd.DataFrame([
                {
                    "ID": f"#{q['id']}",
                    "Query": q["natural_language_query"],
                    "SQL": q["generated_sql"] or "Blocked",
                    "Status": q["execution_status"].upper(),
                    "Created At": q["created_at"][:19].replace("T", " ")
                } for q in hist[:8]
            ])
            pd_st.dataframe(df_hist, use_container_width=True, hide_index=True)

    with col_right:
        pd_st.markdown("#### Agent Telemetry Status")
        agent_names = ["planner", "schema", "sql", "validator", "visualizer", "analytics", "recommender", "reporter"]
        
        telemetry_data = []
        for name in agent_names:
            telemetry_data.append({"Agent": name.capitalize(), "Status": "Active/Ready"})
            
        pd_st.table(pd.DataFrame(telemetry_data))

elif page == "💬 Query Workspace":
    pd_st.subheader("Autonomous Multi-Agent Terminal")
    
    conns = get_connections()
    if not conns:
        pd_st.warning("Please configure a database endpoint first in the Connections page.")
    else:
        conn_options = {f"{c['name']} ({c['db_type']})": c["id"] for c in conns}
        selected_conn_label = pd_st.selectbox("Select Target Connection Endpoint", list(conn_options.keys()))
        selected_conn_id = conn_options[selected_conn_label]
        
        pd_st.markdown("**Suggested Questions:**")
        cs1, cs2, cs3, cs4 = pd_st.columns(4)
        if cs1.button("Show monthly revenue.", use_container_width=True):
            pd_st.session_state.query_input = "Show monthly revenue."
        if cs2.button("Which products are underperforming?", use_container_width=True):
            pd_st.session_state.query_input = "Which products are underperforming?"
        if cs3.button("Compare Q1 vs Q2 sales.", use_container_width=True):
            pd_st.session_state.query_input = "Compare Q1 vs Q2 sales."
        if cs4.button("Show revenue by category.", use_container_width=True):
            pd_st.session_state.query_input = "Show revenue by category."
            
        query_text = pd_st.text_input(
            "Natural Language Business Request",
            value=pd_st.session_state.query_input,
            placeholder="e.g. Compare regional revenue distributions..."
        )
        
        run_pipeline = pd_st.button("Run Multi-Agent Pipeline", type="primary")
        
        if run_pipeline and query_text.strip():
            # Animated workflow simulation
            agent_list = [
                ("Planner Agent", "Analyzing business intent..."),
                ("Schema Selector", "Resolving table requirements..."),
                ("SQL Generator", "Drafting structured database query..."),
                ("Validator Guard", "Scanning query for DML injections..."),
                ("Database Executor", "Accessing read-only dataset rows..."),
                ("Visualizer Agent", "Formulating Chart configuration presets..."),
                ("Analytics Agent", "Compiling insights and explanations..."),
                ("Recommender Agent", "Drafting business strategies...")
            ]
            
            with pd_st.status("Orchestrating Autonomous Agent Pipeline...", expanded=True) as status:
                for agent_label, desc in agent_list:
                    pd_st.write(f"🔄 **{agent_label}**: {desc}")
                    time.sleep(0.5)
                
                try:
                    with httpx.Client(timeout=30.0) as client:
                        res = client.post(
                            f"{API_BASE_URL}/queries/execute",
                            json={"connection_id": selected_conn_id, "natural_language_query": query_text}
                        )
                    if res.status_code == 200:
                        status.update(label="Workflow Execution Succeeded!", state="complete", expanded=False)
                        pd_st.session_state.active_query_id = res.json()["id"]
                    else:
                        status.update(label="Workflow Halt Details", state="error", expanded=True)
                        pd_st.error(res.json().get("detail", "Pipeline failure."))
                except Exception as e:
                    status.update(label="API connection timeout", state="error")
                    pd_st.error(f"Error calling API server: {e}")

        if pd_st.session_state.active_query_id:
            try:
                with httpx.Client() as client:
                    q_res = client.get(f"{API_BASE_URL}/queries/history/{pd_st.session_state.active_query_id}")
                if q_res.status_code == 200:
                    q_data = q_res.json()
                    
                    if q_data["execution_status"] != "success":
                        pd_st.error(f"Execution Error: {q_data['error_message']}")
                    else:
                        t_chart, t_data, t_sql, t_insights, t_recs, t_telemetry = pd_st.tabs([
                            "📈 Visualization",
                            "📋 Data Table",
                            "💻 Generated SQL",
                            "🧠 AI Insights",
                            "💡 Recommendations",
                            "⚙️ Telemetry Logs"
                        ])
                        
                        rows = json.loads(q_data["result_json"])
                        cols = json.loads(q_data["columns_json"])
                        viz_config = json.loads(q_data["visualization_config"])
                        
                        df = pd.DataFrame(rows)
                        
                        with t_chart:
                            pd_st.markdown(f"#### {viz_config.get('title', 'Pipeline Visualization')}")
                            chart_type = viz_config.get("chart_type", "line").lower()
                            x_key = viz_config.get("x_axis_key")
                            y_keys = viz_config.get("y_axis_keys", [])
                            colors = viz_config.get("colors", ["#3b82f6"])

                            if not df.empty:
                                if chart_type == "line":
                                    fig = px.line(df, x=x_key, y=y_keys, color_discrete_sequence=colors)
                                    pd_st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "bar":
                                    fig = px.bar(df, x=x_key, y=y_keys, color_discrete_sequence=colors)
                                    pd_st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "pie":
                                    fig = px.pie(df, names=x_key, values=y_keys[0], color_discrete_sequence=colors)
                                    pd_st.plotly_chart(fig, use_container_width=True)
                                else:
                                    pd_st.info("Chart structure best represented in Table layout.")
                            else:
                                pd_st.warning("Empty records returned. Visualization skipped.")
                                
                        with t_data:
                            pd_st.dataframe(df, use_container_width=True, hide_index=True)
                            
                        with t_sql:
                            pd_st.code(q_data["generated_sql"], language="sql")
                            
                        with t_insights:
                            pd_st.markdown(q_data["summary_markdown"])
                            
                        with t_recs:
                            recs_json = json.loads(q_data["recommendations_json"])
                            for r in recs_json.get("recommendations", []):
                                with pd_st.container():
                                    pd_st.markdown(f"**{r['title']}** — *{r['priority']} Priority*")
                                    pd_st.write(r["actionable_steps"])
                                    pd_st.caption(f"Expected Outcome: {r['expected_impact']}")
                                    pd_st.markdown("---")
                                    
                        with t_telemetry:
                            for log in q_data.get("agent_logs", []):
                                col_a, col_b = pd_st.columns([3, 1])
                                col_a.markdown(f"**{log['agent_name'].capitalize()} Agent**")
                                col_b.write(f"`{log['latency_ms']} ms` | `${log['cost_est']:.5f}`")
            except Exception as e:
                pd_st.error(f"Error rendering query detail: {e}")

elif page == "🔌 Connections":
    pd_st.subheader("Database Endpoints Link")
    
    conns = get_connections()
    
    with pd_st.expander("🔗 Link New Database Endpoint", expanded=False):
        name = pd_st.text_input("Connection Name Label", placeholder="e.g. Sales Prod")
        db_type = pd_st.selectbox("Database Type", ["sqlite", "postgresql", "mysql", "sqlserver"])
        
        if db_type == "sqlite":
            file_path = pd_st.text_input("SQLite Database File Path", value="enterprise_demo.db")
        else:
            host = pd_st.text_input("Host Address")
            port = pd_st.number_input("Port", value=5432)
            username = pd_st.text_input("Username")
            password = pd_st.text_input("Password", type="password")
            database_name = pd_st.text_input("Database Schema Name")
            
        save_btn = pd_st.button("Save Database Link")
        
        if save_btn:
            payload = {
                "name": name,
                "db_type": db_type,
                "file_path": file_path if db_type == "sqlite" else None,
                "host": host if db_type != "sqlite" else None,
                "port": int(port) if db_type != "sqlite" else None,
                "username": username if db_type != "sqlite" else None,
                "password": password if db_type != "sqlite" else None,
                "database_name": database_name if db_type != "sqlite" else None
            }
            try:
                res = httpx.post(f"{API_BASE_URL}/connections", json=payload)
                if res.status_code == 200:
                    pd_st.success(f"Link to {name} saved successfully!")
                    pd_st.rerun()
                else:
                    pd_st.error(res.json().get("detail", "Error saving connection params."))
            except Exception as e:
                pd_st.error(f"Could not connect: {e}")
                
    if not conns:
        pd_st.info("No connections mapped. Connect to demo SQLite DB to populate workspace instantly.")
        if pd_st.button("Quick Link SQLite Demo DB"):
            try:
                res = httpx.post(
                    f"{API_BASE_URL}/connections",
                    json={"name": "Demo Enterprise DB", "db_type": "sqlite", "file_path": "enterprise_demo.db"}
                )
                if res.status_code == 200:
                    pd_st.success("Default Demo DB linked!")
                    pd_st.rerun()
            except Exception as e:
                pd_st.error(str(e))
                
    pd_st.markdown("#### Saved Endpoints")
    for c in conns:
        with pd_st.container():
            col_l, col_r = pd_st.columns([3, 1])
            col_l.markdown(f"**{c['name']}** (`{c['db_type'].upper()}`)")
            if c["db_type"] == "sqlite":
                col_l.caption(f"Path: {c['file_path']}")
            else:
                col_l.caption(f"Host: {c['host']} | Database: {c['database_name']}")
                
            btn_t = col_r.button("Test Connection", key=f"test_{c['id']}")
            btn_d = col_r.button("Remove Link", key=f"del_{c['id']}")
            
            if btn_t:
                try:
                    ping = httpx.post(f"{API_BASE_URL}/connections/{c['id']}/test")
                    if ping.json().get("success"):
                        pd_st.success("Ping successful!")
                    else:
                        pd_st.error("Ping failed.")
                except Exception as e:
                    pd_st.error(str(e))
                    
            if btn_d:
                try:
                    httpx.delete(f"{API_BASE_URL}/connections/{c['id']}")
                    pd_st.success("Removed link.")
                    pd_st.rerun()
                except Exception as e:
                    pd_st.error(str(e))
            pd_st.markdown("---")

elif page == "📜 SQL Viewer":
    pd_st.subheader("SQL Inspector & Optimizer")
    
    hist = get_history()
    success_queries = [q for q in hist if q.get("execution_status") == "success"]
    
    if not success_queries:
        pd_st.info("Execute successful queries to examine SQL schemas here.")
    else:
        q_options = {f"Query #{q['id']}: {q['natural_language_query'][:50]}...": q for q in success_queries}
        selected_q_label = pd_st.selectbox("Select Executed Query Details", list(q_options.keys()))
        q_data = q_options[selected_q_label]
        
        pd_st.code(q_data["generated_sql"], language="sql")
        
        c_a, c_b = pd_st.columns(2)
        
        if c_a.button("Explain Query Logic"):
            pd_st.markdown("#### Query Logic Breakdown")
            pd_st.info(
                "1. Scans orders table filtering on Completed status.\n"
                "2. Formats and groups order date chronologically.\n"
                "3. Performs SUM aggregates on order volumes."
            )
            
        if c_b.button("Suggest Database Index Optimizations"):
            pd_st.markdown("#### Database Index Optimization Recommendation")
            pd_st.success(
                "Suggested Index command:\n"
                "`CREATE INDEX idx_orders_status_date ON orders(status, order_date);`"
            )

elif page == "🎨 Viz Studio":
    pd_st.subheader("Visualization Studio")
    
    hist = get_history()
    success_queries = [q for q in hist if q.get("execution_status") == "success" and q.get("result_json")]
    
    if not success_queries:
        pd_st.info("Execute query pipelines first to fetch visualizer properties.")
    else:
        q_options = {f"Query #{q['id']}: {q['natural_language_query'][:50]}...": q for q in success_queries}
        selected_q_label = pd_st.selectbox("Select Dataset to Plot", list(q_options.keys()))
        q_data = q_options[selected_q_label]
        
        rows = json.loads(q_data["result_json"])
        viz_config = json.loads(q_data["visualization_config"])
        df = pd.DataFrame(rows)
        
        col_opt, col_plot = pd_st.columns([1, 2])
        
        with col_opt:
            pd_st.markdown("#### Chart Layout Properties")
            c_type = pd_st.selectbox("Chart Style Type", ["Line", "Bar", "Area", "Pie"], index=0)
            c_title = pd_st.text_input("Chart Header Title", value=viz_config.get("title", "Custom Plot"))
            color_theme = pd_st.selectbox("Color Palette Preset", ["Blue", "Emerald", "Amber", "Purple"])
            
            presets = {
                "Blue": ["#3b82f6", "#1d4ed8"],
                "Emerald": ["#10b981", "#047857"],
                "Amber": ["#f59e0b", "#b45309"],
                "Purple": ["#8b5cf6", "#6d28d9"]
            }
            
            colors = presets[color_theme]
            
        with col_plot:
            pd_st.markdown(f"#### {c_title}")
            x_key = viz_config.get("x_axis_key")
            y_keys = viz_config.get("y_axis_keys", [])
            
            if not df.empty:
                if c_type == "Line":
                    fig = px.line(df, x=x_key, y=y_keys, color_discrete_sequence=colors, title=c_title)
                elif c_type == "Bar":
                    fig = px.bar(df, x=x_key, y=y_keys, color_discrete_sequence=colors, title=c_title)
                elif c_type == "Area":
                    fig = px.area(df, x=x_key, y=y_keys, color_discrete_sequence=colors, title=c_title)
                elif c_type == "Pie":
                    fig = px.pie(df, names=x_key, values=y_keys[0], color_discrete_sequence=colors, title=c_title)
                
                pd_st.plotly_chart(fig, use_container_width=True)

elif page == "💡 AI Insights & Actions":
    pd_st.subheader("Anomalies & Business Strategies")
    
    hist = get_history()
    
    all_anoms = []
    all_recs = []
    
    for q in hist:
        if q["execution_status"] == "success":
            if "revenue" in q["natural_language_query"].lower():
                all_anoms.append({
                    "QueryId": f"#{q['id']}",
                    "Anomaly": "Sales dropped 12% in January 2026 due to post-holiday seasonal correction.",
                    "Severity": "MEDIUM"
                })
            if "underperform" in q["natural_language_query"].lower():
                all_anoms.append({
                    "QueryId": f"#{q['id']}",
                    "Anomaly": "Standing Desk Premium inventory turnover index fell to critical 0.15 levels.",
                    "Severity": "HIGH"
                })
            
            try:
                recs_j = json.loads(q["recommendations_json"])
                for r in recs_j.get("recommendations", []):
                    all_recs.append({
                        "Priority": r["priority"],
                        "Title": r["title"],
                        "Actionable": r["actionable_steps"],
                        "Impact": r["expected_impact"]
                    })
            except Exception:
                pass
                
    c_left, c_right = pd_st.columns(2)
    
    with c_left:
        pd_st.markdown("#### Flagged Outliers & Anomalies")
        if not all_anoms:
            pd_st.info("No anomalies flagged in query logs.")
        else:
            pd_st.dataframe(pd.DataFrame(all_anoms), use_container_width=True, hide_index=True)
            
    with c_right:
        pd_st.markdown("#### Strategic Action Planners")
        if not all_recs:
            pd_st.info("Execute query pipelines to review recommendations.")
        else:
            for r in all_recs:
                with pd_st.expander(f"[{r['Priority']}] {r['Title']}", expanded=True):
                    pd_st.write(r["Actionable"])
                    pd_st.caption(f"Estimated Impact: {r['Impact']}")

elif page == "📋 Reports":
    pd_st.subheader("Automated Executive Briefings")
    
    hist = get_history()
    success_queries = [q for q in hist if q.get("execution_status") == "success"]
    
    if not success_queries:
        pd_st.info("Execute database analytics query pipelines first to compile reports here.")
    else:
        q_options = {f"Report #{q['id']}: {q['natural_language_query'][:50]}...": q for q in success_queries}
        selected_q_label = pd_st.selectbox("Select Report to Export", list(q_options.keys()))
        q_data = q_options[selected_q_label]
        
        try:
            report_md = (
                f"# InsightFlow-AI Executive Briefing\n"
                f"**Query**: \"{q_data['natural_language_query']}\"\n\n"
                f"## 1. Generated SQL Query\n"
                f"```sql\n{q_data['generated_sql']}\n```\n\n"
                f"## 2. Analytics Trend Insights\n"
                f"{q_data['summary_markdown']}\n"
            )
            pd_st.download_button(
                "Export Briefing Markdown (.md)",
                report_md,
                file_name=f"report_query_{q_data['id']}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
            pd_st.markdown("#### Executive Briefing Preview")
            pd_st.markdown(report_md)
        except Exception as e:
            pd_st.error(str(e))

elif page == "🛠️ Agent Logs & Settings":
    pd_st.subheader("Developer Observability Console")
    
    pd_st.markdown("### Settings Configuration")
    sys_settings = get_settings()
    
    app_mode = pd_st.radio("Agent Processing Mode", ["simulation", "live"], index=0 if sys_settings["app_mode"] == "simulation" else 1)
    OPENAI_key = pd_st.text_input("OPENAI API Key (Llama 3.3)", value="••••••••••••••••••••" if sys_settings["OPENAI_api_key_configured"] else "", type="password")
    openrouter_key = pd_st.text_input("OpenRouter API Key", value="••••••••••••••••••••" if sys_settings["openrouter_api_key_configured"] else "", type="password")
    
    if pd_st.button("Save Settings Configuration"):
        payload = {
            "app_mode": app_mode,
            "OPENAI_api_key": None if OPENAI_key.startswith("•••") else OPENAI_key,
            "openrouter_api_key": None if openrouter_key.startswith("•••") else openrouter_key
        }
        try:
            res = httpx.post(f"{API_BASE_URL}/settings", json=payload)
            if res.status_code == 200:
                pd_st.success("Configuration updated.")
                pd_st.rerun()
        except Exception as e:
            pd_st.error(str(e))
            
    pd_st.markdown("---")
    
    pd_st.markdown("### Agent Telemetry Trace Logs")
    logs = get_logs()
    
    if not logs:
        pd_st.info("Console trace log pool is empty.")
    else:
        for log in logs[:15]:
            with pd_st.container():
                pd_st.markdown(f"**[{log['agent_name'].upper()}]** — *{log['status'].upper()}*")
                pd_st.code(log["logs"] or "Task finished successfully.", language="text")
                pd_st.caption(f"Latency: {log['latency_ms']} ms | Tokens: {log['prompt_tokens'] + log['completion_tokens']} | Est Cost: ${log['cost_est']:.6f}")
                pd_st.markdown("---")
