"""
AQUITARI BRAIN MODELS
---------------------
This script defines the data schemas for the Aquitari Reasoning Engine.
Using Pydantic, it provides:
1. Data Validation: Ensures n8n sends the correct 'state' and 'entity' strings.
2. Serialization: Formats the output from the Knowledge Graph into a clean JSON for the frontend.
3. Documentation: Automatically generates the Swagger UI (OpenAPI) schema for the API.

File: app/models.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import re


class DiagnoseRequest(BaseModel):
    """
    Schema for data entering the Brain from n8n or the Frontend.
    """
    state: str = Field(
        ...,
        example="low_rest",
        description="The biological or system state ID from the Knowledge Graph (e.g., 'low_rest')."
    )
    entity: Optional[str] = Field(
        "local_user",
        example="remad_01",
        description="The identifier for the specific user, agent session, or hardware ID."
    )


class RiskDetail(BaseModel):
    """
    Nested model to describe individual predicted risks discovered in the Graph.
    """
    risk: str
    relation: str


class DiagnoseResponse(BaseModel):
    """
    Schema for data leaving the Brain to go back to n8n/App.
    Ensures the agent always receives a consistent and predictable JSON structure.
    """
    entity: str
    state: str
    timestamp: float
    diagnosis: Dict[str, Any] = Field(
        ...,
        description="The complete reasoning output from the NetworkX engine, including safe_mode status."
    )

    class Config:
        """
        FastAPI Metadata configuration to provide realistic examples in the /docs endpoint.
        """
        json_schema_extra = {
            "example": {
                "entity": "remad_01",
                "state": "low_rest",
                "timestamp": 1705700000.0,
                "diagnosis": {
                    "current_state": "low_rest",
                    "predicted_risks": [
                        {"risk": "executive_fatigue", "relation": "TRIGGERS"}
                    ],
                    "activates_safe_mode": True,
                    "reasoning_path": ["low_rest --[TRIGGERS]--> executive_fatigue"]
                }
            }
        }


# ---------------------------------------------------------
# Utility Function: Robust JSON Extractor
# ---------------------------------------------------------
def extract_json_from_output(raw_output: Any) -> Dict[str, Any]:
    """
    Safely extracts the first valid JSON object from the agent's raw output.
    This makes the system resilient to extra text, Markdown, or formatting
    that may appear after the JSON block.

    Args:
        raw_output (Any): The raw output returned by the agent (string or dict).

    Returns:
        Dict[str, Any]: Parsed JSON dictionary if found, otherwise a safe fallback.

    Notes:
        - Handles cases where the agent appends narrative text after JSON.
        - Cleans fenced code blocks (```json ... ```).
        - Ignores Markdown separators like '---' or '***'.
        - Accepts dicts directly without parsing.
        - Ensures the app always has predictable structured data.
    """
    if raw_output is None:
        return {"reply": "I didn’t get it, please try again."}

    # ✅ Case 1: Already a dict
    if isinstance(raw_output, dict):
        return raw_output

    # ✅ Case 2: String that needs cleanup
    if isinstance(raw_output, str):
        try:
            cleaned = raw_output.strip()

            # Remove fenced code blocks if present
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                cleaned = "\n".join(line for line in lines if not line.strip().startswith("```"))

            # Use regex to find the first JSON object
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    return json.loads(json_str)
                except Exception as e:
                    print("JSON parse error:", e, "Raw after cleanup:", json_str)
                    return {"reply": "I didn’t get it, please try again."}
        except Exception as e:
            print("Extractor error:", e)

    # ✅ Graceful fallback
    return {"reply": "I didn’t get it, please try again."}
    return {}