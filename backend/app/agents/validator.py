import time
import re
from typing import Tuple
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class ValidatorResponse(BaseModel):
    is_valid: bool = Field(description="True if query is safe and correct, False otherwise")
    validation_error: str = Field(description="Detail of why it failed validation, empty string if valid")
    sanitized_sql: str = Field(description="The sanitized SQL query with trailing semicolons or spacing formatted")

class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="validator")

    async def execute(self, sql_query: str) -> Tuple[ValidatorResponse, AgentTelemetry]:
        start_time = time.time()
        
        # 1. Local Python Static Check (Fast and deterministic)
        sanitized = re.sub(r'\s+', ' ', sql_query).strip()
        upper_query = sanitized.upper()
        
        blocked_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "RENAME", "REPLACE", "CREATE", "GRANT", "REVOKE", "MERGE", "EXEC", "SHUTDOWN"]
        for kw in blocked_keywords:
            if re.search(r'\b' + kw + r'\b', upper_query):
                telemetry = self.generate_telemetry(
                    start_time=start_time,
                    status="error",
                    logs=f"Security alert: DML/DDL keyword '{kw}' detected."
                )
                return ValidatorResponse(
                    is_valid=False,
                    validation_error=f"Security Violation: Query attempts to perform write/schema alteration using blocked command '{kw}'.",
                    sanitized_sql=""
                ), telemetry

        # 2. LLM structural verification (checks syntax anomalies or illogical joins)
        system_prompt = (
            "You are the SQL Validator Agent. Your role is to examine a generated SQL query for:\n"
            "1. Syntax correctness.\n"
            "2. Read-only compliance (absolutely no modification keywords).\n"
            "3. Structural issues (such as cartesian joins without join clauses, missing aliases, division by zero).\n"
            "Flag issues with is_valid = False and a clear description."
        )
        
        user_prompt = f"SQL Query to validate:\n{sql_query}"
        
        response: ValidatorResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ValidatorResponse,
            agent_name=self.name
        )
        
        status = "success" if response.is_valid else "error"
        telemetry = self.generate_telemetry(
            start_time=start_time,
            status=status,
            logs=f"Validation result: {'Safe' if response.is_valid else 'Blocked'}. {response.validation_error}"
        )
        
        return response, telemetry
