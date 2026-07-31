import time
from typing import List, Tuple
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class PlannerResponse(BaseModel):
    intent: str = Field(description="The derived user intent (e.g. sales trend, inventory deficit)")
    required_agents: List[str] = Field(description="List of agents needed (e.g. ['schema', 'sql', 'validator'])")
    target_database: str = Field(description="Database engine type (e.g. SQLite, PostgreSQL)")
    suggested_visualization: str = Field(description="Suggested chart layout (e.g. line, bar, pie, scatter)")
    workflow_steps: List[str] = Field(description="Order of execution steps for the workflow")

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="planner")

    async def execute(self, user_query: str, db_type: str) -> Tuple[PlannerResponse, AgentTelemetry]:
        start_time = time.time()
        
        system_prompt = (
            "You are the Lead Planner Agent. Your job is to analyze the user's natural language request, "
            "determine their analytics intent, select which specialized agents are required for the task, "
            "recommend the best type of visualization, and outline the workflow steps.\n\n"
            "Available Agents:\n"
            "- schema (inspect schemas and choose relevant tables)\n"
            "- sql (write the SQL query)\n"
            "- validator (vet the SQL syntax and enforce security read-only checks)\n"
            "- visualizer (choose chart specs and labels)\n"
            "- analytics (explain findings and trends)\n"
            "- recommender (offer concrete business strategies based on data)\n"
            "- reporter (format everything into a neat executive report)\n"
        )
        
        user_prompt = f"User query: '{user_query}'\nTarget Database Type: {db_type}"
        
        response: PlannerResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=PlannerResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Determined intent as: '{response.intent}'. Recommended visualization: {response.suggested_visualization}."
        )
        
        return response, telemetry
