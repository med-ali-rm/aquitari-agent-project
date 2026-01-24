"""
AQUITARI CORE API - SERVER
--------------------------
Description: 
This is the primary gateway for the Aquitari Agent. It exposes a 
RESTful API that allows n8n or other local services to query the 
deterministic Knowledge Graph ('The Brain').


"""

import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from time import time

# Internal imports
from aquitari_core.logic import AquitariBrain
from aquitari_core.models import DiagnoseRequest, DiagnoseResponse

# -------- LOGGING CONFIG --------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Aquitari_Server")

# -------- LIFESPAN MANAGEMENT --------
# Optimized: Load the Brain once during startup and keep it in memory
brain_instance = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    logger.info("Initializing Aquitari Brain...")
    brain_instance["core"] = AquitariBrain()
    logger.info("Brain initialization complete.")
    yield
    # Clean up resources here if needed
    brain_instance.clear()
    logger.info("Aquitari Brain shut down.")

# Initialize FastAPI with lifespan and metadata
app = FastAPI(
    title="Aquitari Local Core",
    description="The 'Brain' of the Aquitari Agent. Handles deterministic logic via Knowledge Graphs.",
    lifespan=lifespan,
    version="1.1.0"
)

# -------- ENDPOINTS --------

@app.get("/health", tags=["System"])
async def health_check():
    """Simple endpoint to verify the server is running and the Brain is loaded."""
    is_ready = "core" in brain_instance
    return {
        "status": "online" if is_ready else "initializing",
        "brain_ready": is_ready
    }

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
    
    # Error Handling: If the state doesn't exist in our JSON data
    if "error" in result:
        logger.warning(f"Diagnosis failed: State '{req.state}' not found in Graph.")
        raise HTTPException(status_code=404, detail=result["error"])

    logger.info(f"Diagnosis completed for {req.entity} in {round(time() - start_time, 4)}s")

    # Successful Response: Structured using the Pydantic model for consistency
    return DiagnoseResponse(
        entity=req.entity,
        state=req.state,
        timestamp=time(),
        diagnosis=result
    )

# -------- RUNNER --------
if __name__ == "__main__":
    # Host '0.0.0.0' is essential for Docker and n8n communication.
    # Port 8000 is the standard port for FastAPI.
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,  # Set to True only during active local development
        log_level="info"
    )