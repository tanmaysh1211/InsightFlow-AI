import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class SQLResponse(BaseModel):
    generated_sql: str = Field(description="The syntactically correct SQL query")
    explanation: str = Field(description="Brief explanation of how the query works")
    dialect: str = Field(description="The SQL dialect targeted (e.g. sqlite, postgresql, mysql)")

class SQLAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="sql")

    async def execute(
        self,
        user_query: str,
        selected_tables: List[str],
        schema_info: List[Dict[str, Any]],
        dialect: str = "sqlite"
    ) -> Tuple[SQLResponse, AgentTelemetry]:
        start_time = time.time()
        
        # Filter schema_info to only selected tables
        filtered_schema = [table for table in schema_info if table["table_name"] in selected_tables]
        
        system_prompt = (
            f"You are the SQL Generation Agent. Your task is to write a syntactically correct, "
            f"highly optimized SQL query targeting the '{dialect}' database dialect.\n"
            f"Instructions:\n"
            f"1. Generate ONLY a single SELECT query.\n"
            f"2. Ensure proper joins using foreign keys when needed.\n"
            f"3. Never perform any data modifications (no INSERT, UPDATE, DELETE, DROP).\n"
            f"4. Format dates and string aggregates properly based on the dialect."
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"Isolated DB Schema for Query:\n{json.dumps(filtered_schema, indent=2)}\n\n"
            f"SQL Dialect: {dialect}"
        )
        
        response: SQLResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=SQLResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Generated {response.dialect} SQL: \n{response.generated_sql}"
        )
        
        return response, telemetry
