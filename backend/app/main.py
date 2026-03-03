from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import router as api_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Saisonale Rohstoff-Analyse mit Prophet + XGBoost",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)
