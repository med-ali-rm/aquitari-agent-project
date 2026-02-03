"""
AQUITARI CORE API - SERVER
--------------------------
Description:
Primary gateway for the Aquitari Agent. Exposes a single POST endpoint
to query the deterministic Knowledge Graph ('The Brain').

Key Features:
- Asynchronous request handling via FastAPI.
- Graph-based reasoning via NetworkX.
- Docker-compatible network binding (0.0.0.0).
- Automatic OpenAPI documentation at /docs.

Author: Aquitari Project
Year: 2026
"""

import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from time import time

# Internal imports
from logic import AquitariBrain
from models import DiagnoseRequest, DiagnoseResponse

# -------- LOGGING CONFIG --------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Aquitari_Server")

# -------- LIFESPAN MANAGEMENT --------
brain_instance = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    logger.info("Initializing Aquitari Brain...")
    brain_instance["core"] = AquitariBrain()
    logger.info("Brain initialization complete.")
    yield
    brain_instance.clear()
    logger.info("Aquitari Brain shut down.")

# -------- FASTAPI APP --------
app = FastAPI(
    title="Aquitari Local Core",
    description="The 'Brain' of the Aquitari Agent. Handles deterministic logic via Knowledge Graphs.",
    lifespan=lifespan,
    version="1.1.0"
)

# -------- ENDPOINT --------
@app.post("/diagnose", response_model=DiagnoseResponse, tags=["Reasoning"])
async def run_diagnose(req: DiagnoseRequest):
    """
    Main Logic Endpoint:
    1. Receives a state (e.g., 'low_rest') from n8n.
    2. Queries the Knowledge Graph for risks and safety protocols.
    3. Returns a structured diagnosis with reasoning paths.
    """
    start_time = time()
    brain = brain_instance.get("core")

    if not brain:
        raise HTTPException(status_code=503, detail="Brain engine is not initialized.")

    # Execute the Graph Search logic
    result = brain.diagnose(req.state)

    # Graceful Handling: If the state doesn't exist in our JSON data
    if "error" in result:
        logger.warning(f"Diagnosis failed: State '{req.state}' not found in Graph.")
        return DiagnoseResponse(
            entity=req.entity,
            state=req.state,
            timestamp=time(),
            diagnosis={
                "info": "No information available in the Knowledge Graph",
                "status": "unknown_state"
            }
        )

    logger.info(f"Diagnosis completed for {req.entity} in {round(time() - start_time, 4)}s")

    return DiagnoseResponse(
        entity=req.entity,
        state=req.state,
        timestamp=time(),
        diagnosis=result
    )

# -------- RUNNER --------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )