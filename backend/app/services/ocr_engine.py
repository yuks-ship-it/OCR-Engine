# backend/app/services/ocr_engine.py
import easyocr
import numpy as np
from app.config import OCR_LANGUAGES

class OCREngine:
    def __init__(self):
        self.reader = easyocr.Reader(OCR_LANGUAGES)

    def read_text(self, image):
        """
        image: numpy array (cropped board)
        returns: extracted text as string
        """
        import cv2
        # Preprocess for better OCR recognition on metallic/reflective boards
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Increase contrast significantly with CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)

        # Optional light denoising (skip heavy denoising which blurs thin letter strokes)
        denoised = cv2.fastNlMeansDenoising(enhanced_gray, None, 5, 7, 21)
        
        # Optional: slight sharpening kernel to make edges of text crisper
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)

        # Let EasyOCR handle the rest of the reading
        result = self.reader.readtext(sharpened, detail=0)
        return '\n'.join(result)