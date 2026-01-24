"""
AQUITARI BRAIN MODELS
---------------------
This script defines the data schemas for the Aquitari Reasoning Engine.
Using Pydantic, it provides:
1. Data Validation: Ensures n8n sends the correct 'state' and 'entity' strings.
2. Serialization: Formats the output from the Knowledge Graph into a clean JSON for the frontend.
3. Documentation: Automatically generates the Swagger UI (OpenAPI) schema for the API.


"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

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