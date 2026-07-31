import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class ActionableRecommendation(BaseModel):
    priority: str = Field(description="Priority: 'HIGH', 'MEDIUM', or 'LOW'")
    title: str = Field(description="Concise strategy title")
    actionable_steps: str = Field(description="Step-by-step instructions on what the business should do")
    expected_impact: str = Field(description="Expected outcome or financial/operational improvements")

class RecommendationResponse(BaseModel):
    recommendations: List[ActionableRecommendation] = Field(description="List of strategic actionable business suggestions")

class RecommendationAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="recommender")

    async def execute(
        self,
        user_query: str,
        analytics_summary: str,
        key_stats: Dict[str, str]
    ) -> Tuple[RecommendationResponse, AgentTelemetry]:
        start_time = time.time()
        
        system_prompt = (
            "You are the Business Recommendation Agent. Your goal is to translate data findings and analytical trends "
            "into concrete, highly actionable recommendations for executives. Every recommendation must list "
            "priority (HIGH/MEDIUM/LOW), a clear title, operational execution steps, and the expected business impact."
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"Analytics Summary:\n{analytics_summary}\n\n"
            f"Key Dataset Stats:\n{json.dumps(key_stats, indent=2)}"
        )
        
        response: RecommendationResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=RecommendationResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Created {len(response.recommendations)} actionable recommendations."
        )
        
        return response, telemetry
