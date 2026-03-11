# backend/app/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Fixed model path (matches train.py output)
MODEL_PATH = BASE_DIR.parent / "runs" / "board_detector" / "weights" / "best.pt"

# EasyOCR languages: English + Nepali
OCR_LANGUAGES = ['en', 'ne']

# YOLO confidence threshold
CONFIDENCE_THRESHOLD = 0.4

# Image preprocessing
PREPROCESS_SCALE_FACTOR = 2     # Upscale factor for small images
CLAHE_CLIP_LIMIT = 3.0          # CLAHE contrast enhancement
DENOISE_STRENGTH = 10           # EasyOCR denoising strength