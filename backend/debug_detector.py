import cv2
import sys
import os
import json

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from services.detector import BoardDetector
from services.ocr_engine import OCREngine
from services.field_parser import FieldParser
from services.qr_reader import QRReader

def run_full_pipeline(image_path):
    with open("debug_output.txt", "w", encoding="utf-8") as out_file:
        out_file.write(f"\n--- Testing: {os.path.basename(image_path)} ---\n")
        img = cv2.imread(image_path)
        if img is None:
            out_file.write("Failed to load image!\n")
            return

        # 1. Test Detection (Contours)
        detector = BoardDetector()
        detections = detector.detect(img)
        
        for det in detections:
            out_file.write(f"BBox: {det['bbox']}\n")
            
            # 2. Test Crop & OCR
            x1, y1, x2, y2 = det['bbox']
            crop = img[y1:y2, x1:x2]
            
            out_file.write("Running OCR...\n")
            ocr = OCREngine()
            ocr_text = ocr.read_text(crop)
            out_file.write(f"Raw OCR Text: \n{ocr_text}\n\n")
            
            # 3. Test Parsers
            parser = FieldParser()
            parsed = parser.parse(ocr_text)
            out_file.write(f"Parsed Fields: {json.dumps(parsed, indent=2, ensure_ascii=False)}\n")

if __name__ == "__main__":
    import pathlib
    base = pathlib.Path(__file__).parent.parent
    val_dir = base / "dataset" / "images" / "val"
    test_image = val_dir / "15.jpeg"  
    run_full_pipeline(str(test_image))
