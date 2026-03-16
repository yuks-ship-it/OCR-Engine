# backend/app/services/roi_extractor.py
import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# ROI layout as (x_frac, y_frac, w_frac, h_frac) of the detected board bbox.
# Calibrated to Kathmandu municipality board design.
# ─────────────────────────────────────────────────────────────────────────────
ROI_FRACTIONS = {
    "street_name":    (0.20, 0.28, 0.65, 0.14),   # ठमेल मार्ग
    "kataho_code":    (0.05, 0.38, 0.92, 0.24),   # कताहो कोड + large number
    "kid_row":        (0.35, 0.57, 0.62, 0.08),   # KID: xx-xxx-xxx-xxxx
    "plus_code":      (0.20, 0.64, 0.62, 0.09),   # Plus code: XXXXXXX+XXX
    "nepali_address": (0.20, 0.73, 0.60, 0.17),   # काठमाडौं महानगरपालिका...
    "qr_code":        (0.80, 0.68, 0.18, 0.22),   # QR code square
}


class ROIExtractor:

    def extract(self, board_crop: np.ndarray) -> dict:
        """
        Given a cropped board image, return a dict of named ROI crops.

        Args:
            board_crop: BGR numpy array of the detected board region

        Returns:
            {
              "street_name":    np.ndarray,
              "kataho_code":    np.ndarray,
              "kid_row":        np.ndarray,
              "plus_code":      np.ndarray,
              "nepali_address": np.ndarray,
              "qr_code":        np.ndarray,
              "coordinates":    { region_name: (x, y, w, h), ... }
            }
        """
        h, w = board_crop.shape[:2]
        crops = {}
        coordinates = {}

        for name, (xf, yf, wf, hf) in ROI_FRACTIONS.items():
            x = int(w * xf)
            y = int(h * yf)
            rw = int(w * wf)
            rh = int(h * hf)

            # Clamp to image bounds
            x  = max(0, min(x,  w - 1))
            y  = max(0, min(y,  h - 1))
            rw = max(1, min(rw, w - x))
            rh = max(1, min(rh, h - y))

            roi_crop = board_crop[y:y + rh, x:x + rw]
            crops[name] = roi_crop
            coordinates[name] = (x, y, rw, rh)

        crops["coordinates"] = coordinates
        return crops

    def draw_rois(self, board_crop: np.ndarray, coordinates: dict) -> np.ndarray:
        """Draw colored ROI boxes on a copy of the board crop (for debugging)."""
        colors = {
            "street_name":    (0, 0, 255),
            "kataho_code":    (255, 0, 255),
            "kid_row":        (0, 165, 255),
            "plus_code":      (255, 255, 0),
            "nepali_address": (0, 255, 255),
            "qr_code":        (128, 0, 255),
        }
        vis = board_crop.copy()
        for name, (x, y, rw, rh) in coordinates.items():
            color = colors.get(name, (255, 255, 255))
            cv2.rectangle(vis, (x, y), (x + rw, y + rh), color, 2)
            cv2.putText(vis, name, (x + 4, y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
        return vis