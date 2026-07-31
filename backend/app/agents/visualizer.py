import time
import json
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentTelemetry
from app.services.llm_service import LLMService

class VisualizationResponse(BaseModel):
    chart_type: str = Field(description="The chart layout: 'line', 'bar', 'pie', 'scatter', or 'table'")
    x_axis_key: str = Field(description="The key from the data to map on the X-axis (e.g. 'month')")
    y_axis_keys: List[str] = Field(description="The keys from the data to plot on the Y-axis (e.g. ['revenue'])")
    title: str = Field(description="Descriptive title for the chart")
    colors: List[str] = Field(default=["#3b82f6", "#10b981", "#f59e0b", "#ef4444"], description="Theme colors to apply to chart bars/lines")

class VisualizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="visualizer")

    async def execute(
        self,
        user_query: str,
        columns: List[Dict[str, str]],
        rows: List[Dict[str, Any]]
    ) -> Tuple[VisualizationResponse, AgentTelemetry]:
        start_time = time.time()
        
        # Take a slice of rows to keep payload compact
        sample_rows = rows[:5]
        
        system_prompt = (
            "You are the Visualization Agent. Your job is to select the optimal chart style to plot the database results "
            "based on the user's natural query and the keys/types present in the returned dataset. "
            "Chart mapping rules:\n"
            "- Time-series or trends -> 'line'\n"
            "- Categories comparison -> 'bar'\n"
            "- Share of total / segments -> 'pie'\n"
            "- Numeric correlations -> 'scatter'\n"
            "- Detailed rows / raw details -> 'table'"
        )
        
        user_prompt = (
            f"User Query: '{user_query}'\n\n"
            f"Columns: {json.dumps(columns)}\n\n"
            f"Data Sample (First 5 rows):\n{json.dumps(sample_rows, indent=2)}"
        )
        
        response: VisualizationResponse = await LLMService.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=VisualizationResponse,
            agent_name=self.name
        )
        
        telemetry = self.generate_telemetry(
            start_time=start_time,
            logs=f"Configured {response.chart_type} chart with X-axis: '{response.x_axis_key}' and Y-axis: {response.y_axis_keys}."
        )
        
        return response, telemetry
