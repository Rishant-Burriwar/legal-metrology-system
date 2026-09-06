import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import engine, Base, seed_database
from app.routers import auth_router, inspections_router, dashboard_router

# Setup directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "images")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_images")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed mandatory rules & default users
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="Legal Metrology Compliance Checking System",
    description="Automated inspection system for packaged commodities compliance under India's Legal Metrology (Packaged Commodities) Rules, 2011.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file storage for images and sample label assets
app.mount("/storage/images", StaticFiles(directory=STORAGE_DIR), name="storage_images")
app.mount("/sample_images", StaticFiles(directory=SAMPLE_DIR), name="sample_images")

# Register Routers
app.include_router(auth_router)
app.include_router(inspections_router)
app.include_router(dashboard_router)


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "system": "Legal Metrology Compliance Checking System",
        "regulatory_standard": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "docs_url": "/docs",
    }
