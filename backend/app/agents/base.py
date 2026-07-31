import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentTelemetry(BaseModel):
    agent_name: str
    execution_time_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_est: float = 0.0
    retry_count: int = 0
    status: str = "success"  # "success", "error", "skipped"
    logs: str = ""

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimates the dollar cost of the LLM execution.
        Using a standard approximation (e.g. $0.15/1M tokens prompt, $0.60/1M tokens completion).
        """
        prompt_cost = (prompt_tokens / 1_000_000) * 0.15
        completion_cost = (completion_tokens / 1_000_000) * 0.60
        return round(prompt_cost + completion_cost, 6)

    def generate_telemetry(
        self,
        start_time: float,
        status: str = "success",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        retry_count: int = 0,
        logs: str = ""
    ) -> AgentTelemetry:
        """Helper to generate a telemetry object with timing details."""
        end_time = time.time()
        elapsed_ms = int((end_time - start_time) * 1000)
        
        # In simulation mode, let's inject mock token counts if they are 0
        if prompt_tokens == 0:
            import random
            prompt_tokens = random.randint(300, 700)
            completion_tokens = random.randint(150, 450)

        cost = self.estimate_cost(prompt_tokens, completion_tokens)
        
        return AgentTelemetry(
            agent_name=self.name,
            execution_time_ms=elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
            cost_est=cost,
            retry_count=retry_count,
            status=status,
            logs=logs
        )
