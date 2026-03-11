# backend/app/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR.parent / "runs" / "detect" / "runs" / "board_detector" / "weights" / "best.pt"
OCR_LANGUAGES = ['en', 'ne']  # Added Nepali support