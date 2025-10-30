from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vastu AI Architect API", 
              description="API for floor plan validation and generation based on Vastu principles",
              version="1.0.0")

# Configure logging to show info-level logs from routers and solvers
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Vastu AI Architect API"}


@app.get("/health")
async def health():
    """Health endpoint for local checks / Electron launcher.

    Returns a small JSON with service status and available solver endpoints.
    """
    return {
        "status": "ok",
        "service": "vastu-ai-architect-backend",
        "version": "1.0.0",
        "routes": [
            "/api/validation",
            "/api/solvers/generate"
        ]
    }

# Import routers
from .routers import validation, solvers
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(solvers.router, prefix="/api/solvers", tags=["solvers"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)