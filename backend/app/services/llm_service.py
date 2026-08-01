import json
import re
import httpx
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

class LLMService:
    @classmethod
    async def call_llm(
        cls,
        system_prompt: str,
        user_prompt: str,
        response_model: Optional[Type[T]] = None,
        agent_name: str = "agent"
    ) -> Any:
        """
        Routes the call to OpenRouter/OPENAI if live mode is enabled and keys exist,
        otherwise falls back to a deterministic simulation engine.
        """
        if settings.APP_MODE == "live" and (settings.OPENAI_API_KEY or settings.OPENROUTER_API_KEY):
            try:
                return await cls._call_live_llm(system_prompt, user_prompt, response_model)
            except Exception as e:
                print(f"Live LLM call failed, falling back to simulator. Error: {e}")

        return cls._run_simulation(agent_name, user_prompt, response_model)

    @classmethod
    async def _call_live_llm(
        cls,
        system_prompt: str,
        user_prompt: str,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """Performs HTTPS calls to OpenRouter or OPENAI with JSON structure support."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if settings.OPENAI_API_KEY:
            url = "https://api.OPENAI.com/openai/v1/chat/completions"
            headers["Authorization"] = f"Bearer {settings.OPENAI_API_KEY}"
            model = "llama-3.3-70b-specdec"
        else:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers["Authorization"] = f"Bearer {settings.OPENROUTER_API_KEY}"
            headers["HTTP-Referer"] = "https://github.com/enterprise-ai-analytics-copilot"
            headers["X-Title"] = "Enterprise AI Analytics Copilot"
            model = "google/gemini-2.5-flash"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        if response_model:
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][0]["content"] += f"\n\nYou must return a JSON object matching this schema:\n{json.dumps(response_model.model_json_schema())}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            content = res_data["choices"][0]["message"]["content"]
            
            if response_model:
                clean_content = re.sub(r"^```json\s*", "", content, flags=re.IGNORECASE)
                clean_content = re.sub(r"\s*```$", "", clean_content, flags=re.IGNORECASE).strip()
                return response_model.model_validate_json(clean_content)
            
            return content

    @classmethod
    def _run_simulation(
        cls,
        agent_name: str,
        user_prompt: str,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Simulates agent outputs based on user prompts and agent target roles.
        Generates realistic enterprise business query structures.
        """
        q = user_prompt.lower()
        
        if agent_name == "planner":
            data = {
                "intent": "revenue_analysis" if "revenue" in q or "sale" in q or "income" in q else "product_analysis",
                "required_agents": ["schema", "sql", "validator", "visualizer", "analytics", "recommender"],
                "target_database": "SQLite",
                "suggested_visualization": "line" if "monthly" in q or "trend" in q or "over time" in q else "bar",
                "workflow_steps": ["Analyze query", "Resolve schemas", "Generate executable SQL", "Verify safety", "Run and plot", "Draft recommendations"]
            }
            
        elif agent_name == "schema":
            if "product" in q or "underperform" in q or "stock" in q:
                tables = ["products", "orders"]
            elif "revenue" in q or "sales" in q or "income" in q or "month" in q:
                tables = ["orders", "payments"]
                if "category" in q or "product" in q:
                    tables.append("products")
            elif "customer" in q or "segment" in q:
                tables = ["customers", "orders"]
            elif "inventory" in q or "supplier" in q or "restock" in q:
                tables = ["inventory", "products"]
            else:
                tables = ["customers", "orders", "products"]
            
            data = {
                "selected_tables": tables,
                "reasoning": f"Identified core entities related to: {user_prompt}. Minimum schema isolation pattern applied."
            }
            
        elif agent_name == "sql":
            sql = ""
            if "monthly" in q or "month" in q:
                sql = (
                    "SELECT strftime('%Y-%m', order_date) AS month, \n"
                    "       SUM(total_amount) AS monthly_revenue, \n"
                    "       COUNT(id) AS total_orders\n"
                    "FROM orders \n"
                    "WHERE status = 'Completed'\n"
                    "GROUP BY month \n"
                    "ORDER BY month ASC;"
                )
            elif "underperform" in q or "worst" in q or "bottom" in q:
                sql = (
                    "SELECT p.name AS product_name, \n"
                    "       SUM(o.quantity) AS units_sold, \n"
                    "       SUM(o.total_amount) AS revenue\n"
                    "FROM products p\n"
                    "LEFT JOIN orders o ON p.id = o.product_id AND o.status = 'Completed'\n"
                    "GROUP BY p.id\n"
                    "ORDER BY units_sold ASC\n"
                    "LIMIT 5;"
                )
            elif "q1 vs q2" in q or "quarter" in q:
                sql = (
                    "SELECT \n"
                    "  CASE \n"
                    "    WHEN order_date LIKE '%-01-%' OR order_date LIKE '%-02-%' OR order_date LIKE '%-03-%' THEN 'Q1'\n"
                    "    WHEN order_date LIKE '%-04-%' OR order_date LIKE '%-05-%' OR order_date LIKE '%-06-%' THEN 'Q2'\n"
                    "    ELSE 'Q3/Q4'\n"
                    "  END AS quarter,\n"
                    "  SUM(total_amount) AS revenue,\n"
                    "  COUNT(id) AS order_count\n"
                    "FROM orders\n"
                    "WHERE status = 'Completed'\n"
                    "GROUP BY quarter\n"
                    "HAVING quarter IN ('Q1', 'Q2');"
                )
            elif "category" in q:
                sql = (
                    "SELECT p.category, \n"
                    "       SUM(o.total_amount) AS total_sales,\n"
                    "       SUM(o.quantity) AS items_sold\n"
                    "FROM orders o\n"
                    "JOIN products p ON o.product_id = p.id\n"
                    "WHERE o.status = 'Completed'\n"
                    "GROUP BY p.category\n"
                    "ORDER BY total_sales DESC;"
                )
            elif "customer" in q or "segment" in q:
                sql = (
                    "SELECT c.segment, \n"
                    "       COUNT(DISTINCT c.id) AS unique_customers,\n"
                    "       SUM(o.total_amount) AS segment_revenue\n"
                    "FROM customers c\n"
                    "LEFT JOIN orders o ON c.id = o.customer_id AND o.status = 'Completed'\n"
                    "GROUP BY c.segment\n"
                    "ORDER BY segment_revenue DESC;"
                )
            else:
                sql = (
                    "SELECT strftime('%Y-%m', order_date) AS month, \n"
                    "       SUM(total_amount) AS revenue \n"
                    "FROM orders \n"
                    "WHERE status = 'Completed' \n"
                    "GROUP BY month \n"
                    "ORDER BY month ASC;"
                )
            data = {
                "generated_sql": sql,
                "explanation": "Calculates aggregation totals based on the order status filter. Optimizes index usage by joining tables via primary foreign keys.",
                "dialect": "sqlite"
            }
            
        elif agent_name == "validator":
            # Check if query contains any bad strings
            is_valid = True
            err_msg = ""
            for bad_word in ["drop", "delete", "update", "insert", "alter", "truncate", "grant"]:
                if bad_word in q:
                    is_valid = False
                    err_msg = f"Security Violation: Query attempts to perform write/schema alterations using blocked command '{bad_word.upper()}'."
                    break
            data = {
                "is_valid": is_valid,
                "validation_error": err_msg,
                "sanitized_sql": user_prompt.replace("SQL Query to validate:\n", "").strip()
            }
            
        elif agent_name == "visualizer":
            chart_type = "bar"
            x_key = ""
            y_keys = []
            
            if "month" in q:
                chart_type = "line"
                x_key = "month"
                y_keys = ["monthly_revenue"]
            elif "underperform" in q or "worst" in q or "product" in q:
                chart_type = "bar"
                x_key = "product_name"
                y_keys = ["units_sold", "revenue"]
            elif "q1 vs q2" in q:
                chart_type = "bar"
                x_key = "quarter"
                y_keys = ["revenue"]
            elif "category" in q:
                chart_type = "pie"
                x_key = "category"
                y_keys = ["total_sales"]
            elif "segment" in q:
                chart_type = "pie"
                x_key = "segment"
                y_keys = ["segment_revenue"]
            else:
                chart_type = "line"
                x_key = "month"
                y_keys = ["revenue"]

            data = {
                "chart_type": chart_type,
                "x_axis_key": x_key,
                "y_axis_keys": y_keys,
                "title": f"Business Analytics Output: {user_prompt.capitalize()}",
                "colors": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"]
            }
            
        elif agent_name == "analytics":
            summary = "Analyzed recent trends in corporate operations."
            anomalies = []
            metrics = {}
            
            if "month" in q:
                summary = "Revenue metrics show positive quarter-over-quarter expansion. Growth peaked in late 2025 followed by a slight post-holiday correction in January 2026."
                anomalies = ["Sales dropped 12% in January 2026 (expected seasonal drop)."]
                metrics = {"growth_rate": "14.2%", "peak_month": "2025-12"}
            elif "underperform" in q:
                summary = "Identified tail-end product units. Physical items like Ergonomic Chairs and Standing Desks suffer from lower sales frequency compared to high-margin SaaS/Software products."
                anomalies = ["Standing Desk Premium registered only 2 units sold."]
                metrics = {"lowest_units_sold": "2", "highest_cost_item": "Developer Laptop Pro"}
            else:
                summary = "Consolidated view of customer operations and product sales distribution across general segments."
                metrics = {"total_records": "25 orders processed"}
                
            data = {
                "summary": summary,
                "key_stats": metrics,
                "anomalies_detected": anomalies
            }
            
        elif agent_name == "recommender":
            recs = []
            if "month" in q:
                recs = [
                    {
                        "priority": "HIGH",
                        "title": "Establish Q3 Seasonal Marketing Push",
                        "actionable_steps": "Invest in targeted software ads beginning in June to capitalize on active budget allocation cycles.",
                        "expected_impact": "Offset Q1 seasonal drop-offs by smoothing customer acquisition."
                    },
                    {
                        "priority": "MEDIUM",
                        "title": "Review SaaS Plan Thresholds",
                        "actionable_steps": "Introduce mid-tier pricing for SaaS hosting accounts to increase average order value.",
                        "expected_impact": "Increase recurring revenue base by 8-12%."
                    }
                ]
            elif "underperform" in q:
                recs = [
                    {
                        "priority": "HIGH",
                        "title": "Furniture Bundle Discount",
                        "actionable_steps": "Package the Ergonomic Chair and Standing Desk together with a 15% discount for corporate customers.",
                        "expected_impact": "Increase standing furniture turnover rates."
                    },
                    {
                        "priority": "LOW",
                        "title": "Supply Chain Reassessment",
                        "actionable_steps": "Review safety stock levels for physical items to reduce warehousing fees.",
                        "expected_impact": "Free up $5,000 in monthly operating capital."
                    }
                ]
            else:
                recs = [
                    {
                        "priority": "MEDIUM",
                        "title": "Conduct Customer Segment Review",
                        "actionable_steps": "Survey Mid-Market clients to see what services could convert them to full Enterprise subscriptions.",
                        "expected_impact": "Increase lifetime value of mid-tier clients."
                    }
                ]
            data = {
                "recommendations": recs
            }
            
        elif agent_name == "reporter":
            data = {
                "report_title": f"Executive Briefing: {user_prompt}",
                "executive_summary": "This briefing details key SQL database extractions. Contains automated schema verification and data execution insights.",
                "sections": [
                    {
                        "heading": "Database Telemetry Summary",
                        "content": "All queries passed syntax validation. Average query execution completed in under 4ms."
                    },
                    {
                        "heading": "Business Recommendation Highlights",
                        "content": "We recommend immediate adjustment of resource pricing and seasonal customer engagement plans."
                    }
                ]
            }
        else:
            data = {"status": "unsupported agent name"}

        if response_model:
            return response_model.model_validate(data)
        
        return json.dumps(data)
