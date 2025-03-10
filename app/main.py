from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path
import os

from app.api.routes import router as api_router
from app.utils.logger import logger

def setup_environment() -> None:
    """Initialize environment variables from .env file in root directory."""
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Environment loaded from: {env_path}")

# Initialize environment variables
setup_environment()

app = FastAPI(
    title="Medical Report Explorer",
    description="A web application for uploading and parsing medical reports in PDF format",
    version="1.0.0",
    # FastAPI will automatically serve the OpenAPI documentation at these endpoints
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 