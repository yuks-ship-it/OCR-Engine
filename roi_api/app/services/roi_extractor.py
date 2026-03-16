# roi_api/app/services/roi_extractor.py

import cv2
import numpy as np
from app.config import ROI_FRACTIONS, ROI_COLORS, ROI_LABELS


class ROIExtractor:

    def extract(self, board_crop: np.ndarray, board_bbox: list) -> dict:
        """
        Extract ROI coordinates from board crop.

        Returns:
            {
                region_name: {
                    "x", "y", "w", "h",          ← relative to board crop
                    "abs_x", "abs_y",             ← in full image
                    "abs_x2", "abs_y2",           ← in full image
                    "label"                       ← human readable name
                }
            }
        """
        h, w   = board_crop.shape[:2]
        bx, by = board_bbox[0], board_bbox[1]
        result = {}

        for name, (xf, yf, wf, hf) in ROI_FRACTIONS.items():
            x  = max(0, int(w * xf))
            y  = max(0, int(h * yf))
            rw = max(1, min(int(w * wf), w - x))
            rh = max(1, min(int(h * hf), h - y))

            result[name] = {
                # Relative to board crop
                "x": x, "y": y, "w": rw, "h": rh,
                # Absolute in full image
                "abs_x":  bx + x,
                "abs_y":  by + y,
                "abs_x2": bx + x + rw,
                "abs_y2": by + y + rh,
                # Label
                "label": ROI_LABELS.get(name, name),
            }

        return result

    def draw(self, image: np.ndarray, board_bbox: list, roi_data: dict) -> np.ndarray:
        """Draw board bbox + ROI boxes on a copy of the image."""
        vis = image.copy()
        bx1, by1, bx2, by2 = board_bbox

        # Board boundary
        cv2.rectangle(vis, (bx1, by1), (bx2, by2), (0, 255, 0), 3)
        cv2.putText(vis, "BOARD", (bx1 + 6, by1 + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # ROI boxes
        for name, c in roi_data.items():
            color = ROI_COLORS.get(name, (255, 255, 255))
            cv2.rectangle(vis, (c["abs_x"], c["abs_y"]),
                          (c["abs_x2"], c["abs_y2"]), color, 2)
            (tw, th), _ = cv2.getTextSize(c["label"],
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(vis,
                          (c["abs_x"], c["abs_y"] - th - 6),
                          (c["abs_x"] + tw + 4, c["abs_y"]),
                          color, -1)
            cv2.putText(vis, c["label"],
                        (c["abs_x"] + 2, c["abs_y"] - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        return vis