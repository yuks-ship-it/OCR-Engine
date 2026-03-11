# backend/app/services/qr_reader.py
import cv2
import numpy as np
from pyzbar.pyzbar import decode


class QRReader:
    def _preprocess_variants(self, image: np.ndarray) -> list:
        """Generate multiple preprocessed variants for better QR detection."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variants = [image, gray]

        # Upscale small images
        if max(image.shape[:2]) < 400:
            upscaled = cv2.resize(image, None, fx=2, fy=2,
                                  interpolation=cv2.INTER_CUBIC)
            variants.append(upscaled)

        # High contrast variant
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        variants.append(enhanced)

        # Thresholded variant
        _, thresh = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(thresh)

        # Sharpened variant
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        variants.append(sharpened)

        return variants

    def read_qr(self, image: np.ndarray) -> list:
        """
        Detect and decode QR codes using multiple preprocessing strategies.
        Returns list of dicts with 'data' and 'type' keys.
        """
        seen = set()
        results = []

        for variant in self._preprocess_variants(image):
            try:
                decoded_objects = decode(variant)
                for obj in decoded_objects:
                    data = obj.data.decode('utf-8', errors='replace').strip()
                    if data and data not in seen:
                        seen.add(data)
                        results.append({
                            "data": data,
                            "type": str(obj.type),
                            "rect": {
                                "left": int(obj.rect.left),
                                "top": int(obj.rect.top),
                                "width": int(obj.rect.width),
                                "height": int(obj.rect.height)
                            }
                        })
            except Exception:
                continue

        return results