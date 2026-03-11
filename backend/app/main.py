# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
from app.config import BASE_DIR

app = FastAPI(
    title="Board OCR System",
    description="OCR Engine for Nepali address boards using OpenCV + EasyOCR",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

frontend_dir = os.path.join(BASE_DIR.parent, "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def root():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Board OCR System is running!", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Server is running"}

@app.get("/{filename}")
def get_static_file(filename: str):
    file_path = os.path.join(frontend_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"message": "File not found"}