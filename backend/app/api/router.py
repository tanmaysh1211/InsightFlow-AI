import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.db.models import DatabaseConnection, QueryHistory, AgentExecutionLog
from app.services.db_executor import DatabaseExecutor
from app.services.llm_service import LLMService
from app.core.config import settings

from app.agents.planner import PlannerAgent
from app.agents.schema import SchemaAgent
from app.agents.sql import SQLAgent
from app.agents.validator import ValidatorAgent
from app.agents.visualizer import VisualizationAgent
from app.agents.analytics import AnalyticsAgent
from app.agents.recommender import RecommendationAgent
from app.agents.reporter import ReportAgent

api_router = APIRouter()

class ConnectionCreate(BaseModel):
    name: str
    db_type: str  # "sqlite", "postgresql", "mysql", "sqlserver"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database_name: Optional[str] = None
    file_path: Optional[str] = None

class ConnectionResponse(BaseModel):
    id: int
    name: str
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    database_name: Optional[str] = None
    file_path: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    connection_id: int
    natural_language_query: str

class AgentLogResponse(BaseModel):
    agent_name: str
    execution_time_ms: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost_est: float
    retry_count: int
    status: str
    logs: Optional[str] = None

class QueryHistoryResponse(BaseModel):
    id: int
    connection_id: Optional[int]
    natural_language_query: str
    generated_sql: Optional[str] = None
    execution_status: str
    error_message: Optional[str] = None
    result_json: Optional[str] = None
    columns_json: Optional[str] = None
    visualization_config: Optional[str] = None
    summary_markdown: Optional[str] = None
    recommendations_json: Optional[str] = None
    created_at: str
    agent_logs: List[AgentLogResponse] = []

    class Config:
        from_attributes = True

class SettingsResponse(BaseModel):
    app_mode: str
    OPENAI_api_key_configured: bool
    openrouter_api_key_configured: bool

class SettingsUpdate(BaseModel):
    app_mode: str
    OPENAI_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

@api_router.post("/connections", response_model=ConnectionResponse)
async def create_connection(data: ConnectionCreate, db: AsyncSession = Depends(get_db)):
    # Verify/Test connection first
    conn_model = DatabaseConnection(
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        username=data.username,
        database_name=data.database_name,
        file_path=data.file_path
    )
    if data.password:
        conn_model.set_password(data.password)

    success, msg = DatabaseExecutor.test_connection(conn_model)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {msg}"
        )

    db.add(conn_model)
    await db.flush()
    await db.commit()
    await db.refresh(conn_model)
    
    return ConnectionResponse(
        id=conn_model.id,
        name=conn_model.name,
        db_type=conn_model.db_type,
        host=conn_model.host,
        port=conn_model.port,
        username=conn_model.username,
        database_name=conn_model.database_name,
        file_path=conn_model.file_path,
        created_at=conn_model.created_at.isoformat()
    )

@api_router.get("/connections", response_model=List[ConnectionResponse])
async def list_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseConnection))
    conns = result.scalars().all()
    return [
        ConnectionResponse(
            id=c.id,
            name=c.name,
            db_type=c.db_type,
            host=c.host,
            port=c.port,
            username=c.username,
            database_name=c.database_name,
            file_path=c.file_path,
            created_at=c.created_at.isoformat()
        ) for c in conns
    ]

@api_router.post("/connections/{conn_id}/test")
async def test_existing_connection(conn_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseConnection).filter(DatabaseConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    success, msg = DatabaseExecutor.test_connection(conn)
    return {"success": success, "message": msg}

@api_router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseConnection).filter(DatabaseConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    await db.delete(conn)
    await db.commit()
    return {"success": True, "message": "Connection deleted successfully."}

@api_router.post("/queries/execute", response_model=QueryHistoryResponse)
async def execute_query_pipeline(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseConnection).filter(DatabaseConnection.id == req.connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection parameters not found.")

    history = QueryHistory(
        connection_id=conn.id,
        natural_language_query=req.natural_language_query,
        execution_status="running"
    )
    db.add(history)
    await db.flush()

    telemetry_logs = []

    try:
        planner = PlannerAgent()
        plan_res, planner_telemetry = await planner.execute(req.natural_language_query, conn.db_type)
        telemetry_logs.append((planner_telemetry, "planner"))

        schema_info = DatabaseExecutor.get_schema_info(conn)

        schema_agent = SchemaAgent()
        schema_res, schema_telemetry = await schema_agent.execute(req.natural_language_query, schema_info)
        telemetry_logs.append((schema_telemetry, "schema"))

        sql_agent = SQLAgent()
        sql_res, sql_telemetry = await sql_agent.execute(
            user_query=req.natural_language_query,
            selected_tables=schema_res.selected_tables,
            schema_info=schema_info,
            dialect=conn.db_type.lower()
        )
        telemetry_logs.append((sql_telemetry, "sql"))
        history.generated_sql = sql_res.generated_sql

        validator_agent = ValidatorAgent()
        val_res, validator_telemetry = await validator_agent.execute(sql_res.generated_sql)
        telemetry_logs.append((validator_telemetry, "validator"))

        if not val_res.is_valid:
            history.execution_status = "blocked"
            history.error_message = val_res.validation_error
            await commit_telemetry(db, history.id, telemetry_logs)
            await db.commit()
            return await format_query_response(history, telemetry_logs)

        rows, columns, db_err = DatabaseExecutor.execute_query(conn, val_res.sanitized_sql)
        if db_err:
            history.execution_status = "error"
            history.error_message = f"Database Execution Error: {db_err}"
            await commit_telemetry(db, history.id, telemetry_logs)
            await db.commit()
            return await format_query_response(history, telemetry_logs)

        history.result_json = json.dumps(rows)
        history.columns_json = json.dumps(columns)

        viz_agent = VisualizationAgent()
        viz_res, viz_telemetry = await viz_agent.execute(req.natural_language_query, columns, rows)
        telemetry_logs.append((viz_telemetry, "visualizer"))
        history.visualization_config = viz_res.model_dump_json()

        analyst = AnalyticsAgent()
        analytics_res, analytics_telemetry = await analyst.execute(req.natural_language_query, columns, rows)
        telemetry_logs.append((analytics_telemetry, "analytics"))
        history.summary_markdown = analytics_res.summary

        recommender = RecommendationAgent()
        recommends_res, recommender_telemetry = await recommender.execute(
            user_query=req.natural_language_query,
            analytics_summary=analytics_res.summary,
            key_stats=analytics_res.key_stats
        )
        telemetry_logs.append((recommender_telemetry, "recommender"))
        history.recommendations_json = recommends_res.model_dump_json()

        reporter = ReportAgent()
        report_res, reporter_telemetry = await reporter.execute(
            user_query=req.natural_language_query,
            sql_query=val_res.sanitized_sql,
            analytics_summary=analytics_res.summary,
            recommendations=[r.model_dump() for r in recommends_res.recommendations]
        )
        telemetry_logs.append((reporter_telemetry, "reporter"))

        history.execution_status = "success"
        
        await commit_telemetry(db, history.id, telemetry_logs)
        await db.commit()

        return await format_query_response(history, telemetry_logs)

    except Exception as e:
        history.execution_status = "error"
        history.error_message = f"Orchestration pipeline exception: {str(e)}"
        await commit_telemetry(db, history.id, telemetry_logs)
        await db.commit()
        return await format_query_response(history, telemetry_logs)

async def commit_telemetry(db: AsyncSession, history_id: int, logs: List[Any]):
    for telemetry, name in logs:
        log_db = AgentExecutionLog(
            query_history_id=history_id,
            agent_name=name,
            execution_time_ms=telemetry.execution_time_ms,
            prompt_tokens=telemetry.prompt_tokens,
            completion_tokens=telemetry.completion_tokens,
            latency_ms=telemetry.latency_ms,
            cost_est=telemetry.cost_est,
            retry_count=telemetry.retry_count,
            status=telemetry.status,
            logs=telemetry.logs
        )
        db.add(log_db)

async def format_query_response(history: QueryHistory, logs: List[Any]) -> QueryHistoryResponse:
    agent_responses = []
    for telemetry, name in logs:
        agent_responses.append(AgentLogResponse(
            agent_name=name,
            execution_time_ms=telemetry.execution_time_ms,
            prompt_tokens=telemetry.prompt_tokens,
            completion_tokens=telemetry.completion_tokens,
            latency_ms=telemetry.latency_ms,
            cost_est=telemetry.cost_est,
            retry_count=telemetry.retry_count,
            status=telemetry.status,
            logs=telemetry.logs
        ))
    return QueryHistoryResponse(
        id=history.id,
        connection_id=history.connection_id,
        natural_language_query=history.natural_language_query,
        generated_sql=history.generated_sql,
        execution_status=history.execution_status,
        error_message=history.error_message,
        result_json=history.result_json,
        columns_json=history.columns_json,
        visualization_config=history.visualization_config,
        summary_markdown=history.summary_markdown,
        recommendations_json=history.recommendations_json,
        created_at=history.created_at.isoformat() if history.created_at else "",
        agent_logs=agent_responses
    )

@api_router.get("/queries/history", response_model=List[QueryHistoryResponse])
async def get_query_history(db: AsyncSession = Depends(get_db)):
    stmt = select(QueryHistory).order_by(desc(QueryHistory.created_at))
    result = await db.execute(stmt)
    histories = result.scalars().all()
    
    response = []
    for h in histories:
        logs_stmt = select(AgentExecutionLog).filter(AgentExecutionLog.query_history_id == h.id)
        logs_res = await db.execute(logs_stmt)
        logs = logs_res.scalars().all()
        
        agent_responses = [
            AgentLogResponse(
                agent_name=l.agent_name,
                execution_time_ms=l.execution_time_ms,
                prompt_tokens=l.prompt_tokens,
                completion_tokens=l.completion_tokens,
                latency_ms=l.latency_ms,
                cost_est=l.cost_est,
                retry_count=l.retry_count,
                status=l.status,
                logs=l.logs
            ) for l in logs
        ]
        
        response.append(QueryHistoryResponse(
            id=h.id,
            connection_id=h.connection_id,
            natural_language_query=h.natural_language_query,
            generated_sql=h.generated_sql,
            execution_status=h.execution_status,
            error_message=h.error_message,
            result_json=h.result_json,
            columns_json=h.columns_json,
            visualization_config=h.visualization_config,
            summary_markdown=h.summary_markdown,
            recommendations_json=h.recommendations_json,
            created_at=h.created_at.isoformat() if h.created_at else "",
            agent_logs=agent_responses
        ))
    return response

@api_router.get("/queries/history/{query_id}", response_model=QueryHistoryResponse)
async def get_query_details(query_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QueryHistory).filter(QueryHistory.id == query_id))
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="Query record not found")
        
    logs_stmt = select(AgentExecutionLog).filter(AgentExecutionLog.query_history_id == h.id)
    logs_res = await db.execute(logs_stmt)
    logs = logs_res.scalars().all()
    
    agent_responses = [
        AgentLogResponse(
            agent_name=l.agent_name,
            execution_time_ms=l.execution_time_ms,
            prompt_tokens=l.prompt_tokens,
            completion_tokens=l.completion_tokens,
            latency_ms=l.latency_ms,
            cost_est=l.cost_est,
            retry_count=l.retry_count,
            status=l.status,
            logs=l.logs
        ) for l in logs
    ]
    
    return QueryHistoryResponse(
        id=h.id,
        connection_id=h.connection_id,
        natural_language_query=h.natural_language_query,
        generated_sql=h.generated_sql,
        execution_status=h.execution_status,
        error_message=h.error_message,
        result_json=h.result_json,
        columns_json=h.columns_json,
        visualization_config=h.visualization_config,
        summary_markdown=h.summary_markdown,
        recommendations_json=h.recommendations_json,
        created_at=h.created_at.isoformat() if h.created_at else "",
        agent_logs=agent_responses
    )

@api_router.get("/queries/history/{query_id}/report")
async def download_query_report(query_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QueryHistory).filter(QueryHistory.id == query_id))
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="Query record not found")
    
    recs = []
    if h.recommendations_json:
        try:
            recs_data = json.loads(h.recommendations_json)
            recs = recs_data.get("recommendations", [])
        except Exception:
            pass
            
    report_md = (
        f"# Enterprise Executive Briefing\n"
        f"**Date Generated**: {h.created_at.strftime('%Y-%m-%d %H:%M:%S') if h.created_at else 'N/A'}\n"
        f"**Source Query**: \"{h.natural_language_query}\"\n"
        f"**Execution Status**: {h.execution_status.upper()}\n\n"
        f"## 1. Technical SQL Context\n"
        f"```sql\n{h.generated_sql}\n```\n\n"
        f"## 2. Analytics Findings & Trend Summarization\n"
        f"{h.summary_markdown or 'No findings summary generated.'}\n\n"
        f"## 3. Strategic Actions & Business Recommendations\n"
    )
    
    if recs:
        for idx, r in enumerate(recs):
            report_md += (
                f"### Recommendation {idx+1}: {r.get('title')} ({r.get('priority')} PRIORITY)\n"
                f"- **Actionable Steps**: {r.get('actionable_steps')}\n"
                f"- **Expected Outcome**: {r.get('expected_impact')}\n\n"
            )
    else:
        report_md += "No actionable strategic recommendations generated.\n"
        
    return Response(content=report_md, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=report_query_{query_id}.md"})

@api_router.get("/queries/logs", response_model=List[AgentLogResponse])
async def get_all_agent_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentExecutionLog).order_by(desc(AgentExecutionLog.id)).limit(100))
    logs = result.scalars().all()
    return [
        AgentLogResponse(
            agent_name=l.agent_name,
            execution_time_ms=l.execution_time_ms,
            prompt_tokens=l.prompt_tokens,
            completion_tokens=l.completion_tokens,
            latency_ms=l.latency_ms,
            cost_est=l.cost_est,
            retry_count=l.retry_count,
            status=l.status,
            logs=l.logs
        ) for l in logs
    ]

@api_router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    return SettingsResponse(
        app_mode=settings.APP_MODE,
        OPENAI_api_key_configured=bool(settings.OPENAI_API_KEY),
        openrouter_api_key_configured=bool(settings.OPENROUTER_API_KEY)
    )

@api_router.post("/settings")
async def update_settings(data: SettingsUpdate):
    settings.APP_MODE = data.app_mode
    if data.OPENAI_api_key is not None:
        settings.OPENAI_API_KEY = data.OPENAI_api_key
    if data.openrouter_api_key is not None:
        settings.OPENROUTER_API_KEY = data.openrouter_api_key
    return {"success": True, "message": "Settings updated successfully."}
