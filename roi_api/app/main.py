# roi_api/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Board ROI API",
    description="Fast API for detecting Kathmandu municipality board and extracting ROI coordinates. No OCR — just board location and region coordinates.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "name":        "Board ROI API",
        "version":     "1.0.0",
        "description": "Detects municipality board and returns ROI coordinates",
        "endpoints": {
            "POST /api/roi":         "Upload image → get board bbox + 6 ROI coordinates",
            "POST /api/roi/batch":   "Upload multiple images → get ROI for each",
            "GET  /api/roi/regions": "Get list of all ROI region names and descriptions",
            "GET  /api/health":      "Health check",
            "GET  /docs":            "Interactive API documentation",
        }
    }