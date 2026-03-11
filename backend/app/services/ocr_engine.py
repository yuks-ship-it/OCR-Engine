# backend/app/services/ocr_engine.py
import cv2
import numpy as np
import easyocr
from app.config import OCR_LANGUAGES


class OCREngine:
    def __init__(self):
        self.reader = easyocr.Reader(OCR_LANGUAGES, gpu=False)

    def _preprocess(self, image: np.ndarray) -> list:
        """
        Returns multiple preprocessed variants to try for best OCR result.
        Handles metallic, reflective, outdoor boards in varied lighting.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Upscale for better OCR on small text
        scale = 2 if max(image.shape[:2]) < 800 else 1
        if scale > 1:
            gray = cv2.resize(gray, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)

        variants = []

        # Variant 1: CLAHE enhanced
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        sharp_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, sharp_kernel)
        variants.append(sharpened)

        # Variant 2: Otsu thresholding (good for high-contrast boards)
        _, otsu = cv2.threshold(enhanced, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)

        # Variant 3: Adaptive threshold (good for uneven lighting)
        adaptive = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 8
        )
        variants.append(adaptive)

        # Variant 4: Inverted (for light text on dark boards)
        variants.append(cv2.bitwise_not(otsu))

        return variants

    def read_text(self, image: np.ndarray) -> str:
        """
        Run OCR on multiple preprocessed variants and return
        the result with the highest combined confidence score.
        """
        variants = self._preprocess(image)
        best_text = ""
        best_score = -1.0

        for variant in variants:
            try:
                results = self.reader.readtext(variant, detail=1)
                if not results:
                    continue

                # Filter low-confidence results
                filtered = [r for r in results if r[2] > 0.2]
                if not filtered:
                    continue

                avg_confidence = float(np.mean([r[2] for r in filtered]))
                text = '\n'.join([r[1] for r in filtered])

                if avg_confidence > best_score:
                    best_score = avg_confidence
                    best_text = text

            except Exception:
                continue

        return best_text

    def read_text_with_details(self, image: np.ndarray) -> dict:
        """
        Returns text along with per-word bounding boxes and confidence scores.
        Useful for structured field extraction.
        """
        variants = self._preprocess(image)
        best_results = []
        best_score = -1.0

        for variant in variants:
            try:
                results = self.reader.readtext(variant, detail=1)
                if not results:
                    continue
                filtered = [r for r in results if r[2] > 0.2]
                if not filtered:
                    continue
                avg_confidence = float(np.mean([r[2] for r in filtered]))
                if avg_confidence > best_score:
                    best_score = avg_confidence
                    best_results = filtered
            except Exception:
                continue

        words = [
            {
                "text": r[1],
                "confidence": round(r[2], 3),
                "bbox": r[0]
            }
            for r in best_results
        ]
        full_text = '\n'.join([w["text"] for w in words])

        return {
            "text": full_text,
            "words": words,
            "avg_confidence": round(best_score, 3) if best_score >= 0 else 0.0
        }