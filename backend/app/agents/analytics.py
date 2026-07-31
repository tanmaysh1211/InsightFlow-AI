import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class AnalyticsResponse(BaseModel):
    summary: str = Field(description="Markdown summarized business insights of the data")
    key_stats: Dict[str, str] = Field(description="Dictionary of calculated stats like averages, max, min, totals")
    anomalies_detected: List[str] = Field(description="List of detected anomalies, empty if none")

class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="analytics")

    async def execute(
        self,
        user_query: str,
        columns: List[Dict[str, str]],
        rows: List[Dict[str, Any]]
    ) -> Tuple[AnalyticsResponse, AgentTelemetry]:
        start_time = time.time()
        
        system_prompt = (
            "You are the Analytics Agent. Your goal is to inspect a query result dataset, "
            "perform business intelligence aggregation, calculate key metrics, explain the trends, "
            "and call out any statistical anomalies (e.g. dramatic drops, spikes, outliers, zero levels)."
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"Columns: {json.dumps(columns)}\n\n"
            f"Full Dataset (JSON):\n{json.dumps(rows, indent=2)}"
        )
        
        response: AnalyticsResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AnalyticsResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Analytics generated. Summary size: {len(response.summary)} chars. Detected {len(response.anomalies_detected)} anomalies."
        )
        
        return response, telemetry
