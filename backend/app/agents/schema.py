import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class SchemaResponse(BaseModel):
    selected_tables: List[str] = Field(description="List of table names selected as relevant for the user query")
    reasoning: str = Field(description="Explanation of why these tables were chosen and others excluded")

class SchemaAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="schema")

    async def execute(self, user_query: str, schema_info: List[Dict[str, Any]]) -> Tuple[SchemaResponse, AgentTelemetry]:
        start_time = time.time()
        
        # Serialize schema info briefly to save tokens
        schema_summary = []
        for table in schema_info:
            cols = [f"{col['name']} ({col['type']})" for col in table.get("columns", [])]
            schema_summary.append({
                "table_name": table["table_name"],
                "columns": cols,
                "foreign_keys": table.get("foreign_keys", [])
            })
            
        system_prompt = (
            "You are the Schema Selection Agent. Your goal is to inspect the full schema metadata of a database "
            "and identify the minimum subset of tables required to answer the user's natural language request. "
            "Excluding irrelevant tables prevents the SQL Agent from getting confused by complex schemas."
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"Full Database Schema:\n{json.dumps(schema_summary, indent=2)}"
        )
        
        response: SchemaResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=SchemaResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Selected tables: {response.selected_tables}. Reasoning: {response.reasoning}"
        )
        
        return response, telemetry
