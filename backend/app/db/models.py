from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cryptography.fernet import Fernet
from app.core.database import Base
from app.core.config import settings

# Fernet encryption setup
def get_fernet() -> Fernet:
    # Ensure key is valid base64 32-byte key
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception:
        # Fallback if key is not base64: generate deterministic one
        import base64
        import hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest())
        return Fernet(key)

class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    db_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "sqlite", "postgresql", "mysql", "sqlserver"
    host: Mapped[str] = mapped_column(String(255), nullable=True)
    port: Mapped[int] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    password_enc: Mapped[str] = mapped_column(Text, nullable=True)  # encrypted password
    database_name: Mapped[str] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=True)  # path to SQLite DB file
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    queries: Mapped[list["QueryHistory"]] = relationship("QueryHistory", back_populates="connection", cascade="all, delete-orphan")

    def set_password(self, password: str):
        if password:
            f = get_fernet()
            self.password_enc = f.encrypt(password.encode()).decode()
        else:
            self.password_enc = None

    def get_password(self) -> str:
        if self.password_enc:
            f = get_fernet()
            return f.decrypt(self.password_enc.encode()).decode()
        return ""

class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(Integer, ForeignKey("database_connections.id", ondelete="SET NULL"), nullable=True)
    natural_language_query: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(50), default="pending")  # "success", "error", "blocked"
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    result_json: Mapped[str] = mapped_column(Text, nullable=True)  # results rows as JSON list of dicts
    columns_json: Mapped[str] = mapped_column(Text, nullable=True)  # schema / columns definition
    visualization_config: Mapped[str] = mapped_column(Text, nullable=True)  # chart config details as JSON
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=True)  # text explanation of insights
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON representation of recommendations
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    connection: Mapped[DatabaseConnection] = relationship("DatabaseConnection", back_populates="queries")
    agent_logs: Mapped[list["AgentExecutionLog"]] = relationship("AgentExecutionLog", back_populates="query", cascade="all, delete-orphan")

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query_history_id: Mapped[int] = mapped_column(Integer, ForeignKey("query_history.id", ondelete="CASCADE"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_est: Mapped[float] = mapped_column(Float, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="success")  # "success", "error", "skipped"
    logs: Mapped[str] = mapped_column(Text, nullable=True)

    query: Mapped[QueryHistory] = relationship("QueryHistory", back_populates="agent_logs")
