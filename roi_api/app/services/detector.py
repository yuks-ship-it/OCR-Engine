# roi_api/app/services/detector.py

import cv2
import numpy as np


class BoardDetector:

    BLUE_LOWER = np.array([90,  80,  60])
    BLUE_UPPER = np.array([135, 255, 255])

    def detect(self, image: np.ndarray) -> dict | None:
        """
        Detect the blue municipality board.
        Returns dict with bbox, confidence, crop — or None if not found.
        """
        result = self._by_color(image)
        if result:
            return result
        return self._by_edges(image)

    def _by_color(self, image):
        h, w = image.shape[:2]
        hsv  = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.BLUE_LOWER, self.BLUE_UPPER)

        k    = np.ones((15, 15), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None

        best = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(best) < w * h * 0.05:
            return None

        bx, by, bw, bh = cv2.boundingRect(best)
        if not (0.8 < bw / bh < 4.0):
            return None

        peri   = cv2.arcLength(best, True)
        approx = cv2.approxPolyDP(best, 0.02 * peri, True)
        crop   = self._deskew(image, approx) if len(approx) == 4 else None
        if crop is None or crop.size == 0:
            crop = image[by:by + bh, bx:bx + bw]

        return {"bbox": [bx, by, bx + bw, by + bh], "confidence": 0.95, "crop": crop}

    def _by_edges(self, image):
        h, w    = image.shape[:2]
        gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe   = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray    = clahe.apply(gray)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        adaptive = cv2.adaptiveThreshold(blurred, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5)
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged   = cv2.Canny(cv2.dilate(adaptive, kernel, iterations=2), 30, 120)

        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None

        for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:10]:
            peri   = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(c) > w * h * 0.04:
                bx, by, bw, bh = cv2.boundingRect(approx)
                if 0.3 < bw / bh < 5.0:
                    crop = self._deskew(image, approx)
                    if crop is not None and crop.size > 0:
                        return {"bbox": [bx, by, bx + bw, by + bh],
                                "confidence": 0.75, "crop": crop}
        return None

    def _deskew(self, image, approx):
        if approx is None or len(approx) != 4:
            return None
        try:
            pts  = approx.reshape(4, 2).astype("float32")
            s    = pts.sum(axis=1)
            d    = np.diff(pts, axis=1)
            rect = np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                             pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")
            tl, tr, br, bl = rect
            maxW = max(int(np.linalg.norm(br - bl)), int(np.linalg.norm(tr - tl)))
            maxH = max(int(np.linalg.norm(tr - br)), int(np.linalg.norm(tl - bl)))
            if maxW < 10 or maxH < 10:
                return None
            dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
            return cv2.warpPerspective(image, cv2.getPerspectiveTransform(rect, dst), (maxW, maxH))
        except Exception:
            return None