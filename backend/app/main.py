from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vastu AI Architect API", 
              description="API for floor plan validation and generation based on Vastu principles",
              version="1.0.0")

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

# Import routers
from .routers import validation, solvers
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(solvers.router, prefix="/api/solvers", tags=["solvers"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)