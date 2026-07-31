import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.database import init_metadata_db
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Multi-Agent Business Analytics Engine & SQL Generation Workspace",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initializes tables on startup."""
    print("Initializing Metadata database and models...")
    await init_metadata_db()
    print("Metadata database ready.")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "mode": settings.APP_MODE
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
