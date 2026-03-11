# backend/app/api/routes.py
import cv2
import base64
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.detector import BoardDetector
from app.services.ocr_engine import OCREngine
from app.services.qr_reader import QRReader
from app.services.field_parser import FieldParser

router = APIRouter()

# Initialize services once at startup
detector = BoardDetector()
ocr = OCREngine()
qr_reader = QRReader()
parser = FieldParser()


def to_python(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: to_python(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_python(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def encode_image(img: np.ndarray) -> str:
    """Encode a numpy image to base64 JPEG string for frontend display."""
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer).decode('utf-8')


def draw_annotations(img: np.ndarray, detections: list) -> np.ndarray:
    """Draw bounding boxes and OCR text on the original image."""
    annotated = img.copy()
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        label = det.get('ocr_text', '')[:40]
        conf = det.get('confidence', 0)

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 100), 2)

        # Draw label background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 200, 100), -1)

        # Draw label text
        cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

        # Draw confidence
        cv2.putText(annotated, f"{conf:.0%}", (x2 - 40, y2 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    return annotated


@router.post("/process")
async def process_image(file: UploadFile = File(...)):
    """
    Accept an image, detect boards, run OCR + QR reading,
    parse fields, and return all extracted data with annotated image.
    """
    try:
        # ── Read uploaded image ───────────────────────────────────────────────
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file.")

        # ── Detect boards ─────────────────────────────────────────────────────
        detections = detector.detect(img)

        results = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']

            # Use deskewed crop if available, else use raw crop
            crop = det.get('deskewed') if det.get('deskewed') is not None else img[y1:y2, x1:x2]

            if crop is None or crop.size == 0:
                continue

            # ── OCR ───────────────────────────────────────────────────────────
            ocr_details = ocr.read_text_with_details(crop)
            ocr_text = ocr_details["text"]
            ocr_confidence = ocr_details["avg_confidence"]

            # ── QR Code ───────────────────────────────────────────────────────
            qr_data = qr_reader.read_qr(crop)

            # ── Field Parsing ─────────────────────────────────────────────────
            parsed_fields = parser.parse(ocr_text)

            # ── Cropped board as base64 ───────────────────────────────────────
            crop_b64 = encode_image(crop)

            results.append(to_python({
                "bbox": [x1, y1, x2, y2],
                "detection_confidence": round(float(det['confidence']), 3),
                "class": det['class'],
                "ocr_text": ocr_text,
                "ocr_confidence": float(ocr_confidence),
                "ocr_words": [
                    {"text": w["text"], "confidence": float(w["confidence"])}
                    for w in ocr_details.get("words", [])
                ],
                "qr_data": qr_data,
                "parsed_fields": parsed_fields,
                "cropped_image": crop_b64,
            }))

        # ── Annotated full image ──────────────────────────────────────────────
        annotated_img = draw_annotations(img, results)
        annotated_b64 = encode_image(annotated_img)

        return {
            "success": True,
            "total_detections": len(results),
            "detections": results,
            "annotated_image": annotated_b64,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.post("/process/camera")
async def process_camera_frame(file: UploadFile = File(...)):
    """
    Same as /process but optimised label for live camera frames.
    Reuses the same pipeline.
    """
    return await process_image(file)


@router.get("/health")
def health():
    return {"status": "ok", "services": ["detector", "ocr", "qr_reader", "field_parser"]}