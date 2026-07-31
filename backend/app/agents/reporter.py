import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class ReportSection(BaseModel):
    heading: str = Field(description="Section heading/title")
    content: str = Field(description="Detailed markdown text of this section")

class ReportResponse(BaseModel):
    report_title: str = Field(description="Formal title of the executive briefing")
    executive_summary: str = Field(description="A concise executive overview of the report findings")
    sections: List[ReportSection] = Field(description="Structured chapters compiling analysis, SQL data, and strategies")

class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="reporter")

    async def execute(
        self,
        user_query: str,
        sql_query: str,
        analytics_summary: str,
        recommendations: List[Dict[str, Any]]
    ) -> Tuple[ReportResponse, AgentTelemetry]:
        start_time = time.time()
        
        system_prompt = (
            "You are the executive Report Agent. Your role is to aggregate the database query details, "
            "the executed SQL, the analytics insights, and the recommendations into a publication-ready, "
            "structured executive briefing. Organize it into descriptive logical chapters."
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"SQL Executed:\n{sql_query}\n\n"
            f"Analytics Insights:\n{analytics_summary}\n\n"
            f"Recommendations:\n{json.dumps(recommendations, indent=2)}"
        )
        
        response: ReportResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ReportResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Compiled executive report with {len(response.sections)} structured chapters."
        )
        
        return response, telemetry
