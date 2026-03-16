# roi_api/app/api/routes.py

import cv2
import base64
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.detector    import BoardDetector
from app.services.roi_extractor import ROIExtractor
from app.config               import ROI_LABELS, ROI_FRACTIONS

router   = APIRouter()
detector = BoardDetector()
extractor = ROIExtractor()


def encode_image(img: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/roi  — single image
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/roi")
async def get_roi(
    file: UploadFile = File(..., description="Board image (jpg/png)"),
    include_image: bool = False,
):
    """
    Upload a board image and get back the board bounding box
    and all 6 ROI region coordinates.

    - **include_image**: set to true to also get the annotated image as base64
    """
    try:
        contents = await file.read()
        np_arr   = np.frombuffer(contents, np.uint8)
        img      = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid or unreadable image.")

        img_h, img_w = img.shape[:2]

        # ── Detect board ──────────────────────────────────────────────────────
        board = detector.detect(img)

        if board is None:
            return {
                "success":         False,
                "error":           "No board detected in image.",
                "image_size":      {"width": img_w, "height": img_h},
                "board":           None,
                "roi_coordinates": {},
            }

        x1, y1, x2, y2 = board["bbox"]
        crop            = board["crop"]

        # ── Extract ROI coordinates ───────────────────────────────────────────
        roi_data = extractor.extract(crop, board["bbox"])

        # Clean output — separate relative and absolute coords
        roi_relative = {}
        roi_absolute = {}
        for name, c in roi_data.items():
            roi_relative[name] = {
                "x": c["x"], "y": c["y"],
                "w": c["w"], "h": c["h"],
                "label": c["label"],
            }
            roi_absolute[name] = {
                "x":  c["abs_x"],
                "y":  c["abs_y"],
                "w":  c["w"],
                "h":  c["h"],
                "x2": c["abs_x2"],
                "y2": c["abs_y2"],
                "label": c["label"],
            }

        response = {
            "success": True,

            # Image info
            "image_size": {"width": img_w, "height": img_h},

            # Board location in the full image
            "board": {
                "x1":         x1,
                "y1":         y1,
                "x2":         x2,
                "y2":         y2,
                "width":      x2 - x1,
                "height":     y2 - y1,
                "confidence": round(float(board["confidence"]), 3),
            },

            # ROI coords relative to board crop
            "roi_coordinates": roi_relative,

            # ROI coords in full image space
            "roi_full_coords": roi_absolute,
        }

        # Optional annotated image
        if include_image:
            annotated = extractor.draw(img, board["bbox"], roi_data)
            response["annotated_image"] = encode_image(annotated)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/roi/batch  — multiple images at once
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/roi/batch")
async def get_roi_batch(
    files: list[UploadFile] = File(..., description="Multiple board images"),
):
    """
    Upload multiple board images and get ROI coordinates for each.
    """
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 images per batch.")

    results = []
    for f in files:
        try:
            contents = await f.read()
            np_arr   = np.frombuffer(contents, np.uint8)
            img      = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                results.append({"filename": f.filename, "success": False,
                                 "error": "Invalid image"})
                continue

            board = detector.detect(img)
            if board is None:
                results.append({"filename": f.filename, "success": False,
                                 "error": "No board detected"})
                continue

            roi_data = extractor.extract(board["crop"], board["bbox"])
            x1, y1, x2, y2 = board["bbox"]

            roi_absolute = {}
            for name, c in roi_data.items():
                roi_absolute[name] = {
                    "x": c["abs_x"], "y": c["abs_y"],
                    "w": c["w"],     "h": c["h"],
                    "x2": c["abs_x2"], "y2": c["abs_y2"],
                    "label": c["label"],
                }

            results.append({
                "filename": f.filename,
                "success":  True,
                "board": {
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "confidence": round(float(board["confidence"]), 3),
                },
                "roi_full_coords": roi_absolute,
            })

        except Exception as e:
            results.append({"filename": f.filename, "success": False,
                             "error": str(e)})

    return {
        "total":   len(files),
        "success": sum(1 for r in results if r["success"]),
        "failed":  sum(1 for r in results if not r["success"]),
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/roi/regions  — list all region definitions
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/roi/regions")
def get_regions():
    """
    Returns the list of all 6 ROI regions with their names,
    labels, and fractional positions.
    """
    return {
        "total":   len(ROI_FRACTIONS),
        "regions": [
            {
                "name":    name,
                "label":   ROI_LABELS.get(name, name),
                "x_frac":  xf,
                "y_frac":  yf,
                "w_frac":  wf,
                "h_frac":  hf,
            }
            for name, (xf, yf, wf, hf) in ROI_FRACTIONS.items()
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/health
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    return {
        "status":   "ok",
        "services": ["board_detector", "roi_extractor"],
    }