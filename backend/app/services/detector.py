# backend/app/services/detector.py
import cv2
import numpy as np


class BoardDetector:
    def __init__(self):
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

        widthA  = np.linalg.norm(br - bl)
        widthB  = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))

        heightA  = np.linalg.norm(tr - br)
        heightB  = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))

        if maxWidth < 10 or maxHeight < 10:
            return None

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    def _detect_by_color(self, image: np.ndarray):
        """
        Primary method: detect the blue board using HSV color segmentation.
        Works reliably for the Kathmandu municipality blue board.
        """
        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Blue color range — covers the municipality board blue
        # Slightly wide range to handle different lighting conditions
        lower_blue = np.array([90,  80,  60])
        upper_blue = np.array([135, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Clean up the mask
        kernel = np.ones((15, 15), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Pick the largest blue region
        best = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(best)

        # Must cover at least 5% of the frame
        if area < width * height * 0.05:
            return None

        x, y, w, h = cv2.boundingRect(best)
        aspect = w / h if h != 0 else 0

        # Sanity check aspect ratio (board is wider than tall)
        if not (0.8 < aspect < 4.0):
            return None

        # Try to get a clean 4-point contour for deskewing
        peri   = cv2.arcLength(best, True)
        approx = cv2.approxPolyDP(best, 0.02 * peri, True)

        deskewed = None
        if len(approx) == 4:
            deskewed = self._deskew(image, approx)

        if deskewed is None or deskewed.size == 0:
            deskewed = image[y:y + h, x:x + w]

        return {
            'bbox':       [x, y, x + w, y + h],
            'confidence': 0.95,
            'class':      'board',
            'deskewed':   deskewed
        }

    def _detect_by_edges(self, image: np.ndarray):
        """
        Fallback method: edge + contour detection.
        Used only when color detection fails (unusual lighting / non-blue boards).
        """
        height, width = image.shape[:2]
        gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe   = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray    = clahe.apply(gray)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        adaptive = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(adaptive, kernel, iterations=2)
        edged   = cv2.Canny(dilated, 30, 120)

        cnts, _ = cv2.findContours(
            edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not cnts:
            return None

        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]

        for c in cnts:
            peri   = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            area   = cv2.contourArea(c)

            if len(approx) == 4 and area > (width * height * 0.04):
                x, y, w, h = cv2.boundingRect(approx)
                aspect = w / h if h != 0 else 0
                if 0.3 < aspect < 5.0:
                    deskewed = self._deskew(image, approx)
                    if deskewed is not None and deskewed.size > 0:
                        return {
                            'bbox':       [x, y, x + w, y + h],
                            'confidence': 0.80,
                            'class':      'board',
                            'deskewed':   deskewed
                        }

        # Largest contour fallback
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w * h > (width * height * 0.05):
                return {
                    'bbox':       [x, y, x + w, y + h],
                    'confidence': 0.65,
                    'class':      'board',
                    'deskewed':   image[y:y + h, x:x + w]
                }

        return None

    def detect(self, image: np.ndarray, conf_threshold: float = 0.1):
        """
        Detect the municipality board in the image.

        Detection order:
          1. Blue color segmentation  (fast, accurate for blue boards)
          2. Edge + contour detection (fallback for tricky lighting)
          3. Full frame               (last resort, always succeeds)
        """
        height, width = image.shape[:2]

        # ── Step 1: Try color-based detection first ───────────────────────────
        result = self._detect_by_color(image)
        if result:
            return [result]

        # ── Step 2: Try edge-based detection ─────────────────────────────────
        result = self._detect_by_edges(image)
        if result:
            return [result]

        # ── Step 3: Full frame fallback ───────────────────────────────────────
        margin_x = int(width  * 0.05)
        margin_y = int(height * 0.05)
        cropped  = image[margin_y:height - margin_y, margin_x:width - margin_x]
        return [{
            'bbox':       [margin_x, margin_y, width - margin_x, height - margin_y],
            'confidence': 0.40,
            'class':      'board (full frame)',
            'deskewed':   cropped
        }]