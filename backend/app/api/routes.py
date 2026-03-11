# backend/app/api/routes.py
from fastapi import APIRouter, File, UploadFile, HTTPException
import cv2
import numpy as np
from app.services.detector import BoardDetector
from app.services.ocr_engine import OCREngine
from app.services.qr_reader import QRReader
from app.services.field_parser import FieldParser

router = APIRouter()

# Initialize services
detector = BoardDetector()
ocr = OCREngine()
qr_reader = QRReader()
parser = FieldParser()

@router.post("/process")
async def process_image(file: UploadFile = File(...)):
    """
    Accept an image, detect boards, run OCR and QR reading, and return extracted data.
    """
    try:
        # Read image
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        # Detect boards
        detections = detector.detect(img)

        results = []
        for det in detections:
            # Crop board region
            x1, y1, x2, y2 = det['bbox']
            crop = img[y1:y2, x1:x2]

            # Run OCR
            ocr_text = ocr.read_text(crop)

            # Run QR detection (optional)
            qr_data = qr_reader.read_qr(crop)

            # Parse fields (e.g., extract license plate number)
            parsed = parser.parse(ocr_text)

            results.append({
                "bbox": det['bbox'],
                "confidence": det['confidence'],
                "class": det['class'],
                "ocr_text": ocr_text,
                "qr_data": qr_data,
                "parsed": parsed
            })

        return {"success": True, "detections": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))