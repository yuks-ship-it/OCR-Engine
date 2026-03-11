# backend/app/services/detector.py
import cv2
import numpy as np


class BoardDetector:
    def __init__(self):
        # Uses OpenCV computer vision for reliable board extraction
        pass

    def _order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def _deskew(self, image, approx):
        """Correct perspective distortion on detected board."""
        pts = approx.reshape(4, 2).astype("float32")
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    def detect(self, image: np.ndarray, conf_threshold: float = 0.1):
        height, width = image.shape[:2]

        # --- Multi-scale preprocessing for metallic/reflective boards ---
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # CLAHE to handle reflective/metallic board surfaces
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Adaptive thresholding works better than Canny for varied lighting
        adaptive = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )

        # Dilate to connect broken edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(adaptive, kernel, iterations=2)

        edged = cv2.Canny(dilated, 30, 120)

        cnts, _ = cv2.findContours(
            edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if cnts:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]

            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                area = cv2.contourArea(c)

                # 4-point quad detection with deskew
                if len(approx) == 4 and area > (width * height * 0.04):
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect = w / h if h != 0 else 0

                    # Filter unrealistic aspect ratios
                    if 0.3 < aspect < 5.0:
                        deskewed = self._deskew(image, approx)
                        return [{
                            'bbox': [x, y, x + w, y + h],
                            'confidence': 0.95,
                            'class': 'board',
                            'deskewed': deskewed
                        }]

            # Fallback: largest contour by bounding rect
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if w * h > (width * height * 0.05):
                    cropped = image[y:y + h, x:x + w]
                    return [{
                        'bbox': [x, y, x + w, y + h],
                        'confidence': 0.80,
                        'class': 'board',
                        'deskewed': cropped
                    }]

        # Ultimate fallback: full frame with small margin
        margin_x = int(width * 0.05)
        margin_y = int(height * 0.05)
        cropped = image[margin_y:height - margin_y, margin_x:width - margin_x]
        return [{
            'bbox': [margin_x, margin_y, width - margin_x, height - margin_y],
            'confidence': 0.50,
            'class': 'board (full frame)',
            'deskewed': cropped
        }]