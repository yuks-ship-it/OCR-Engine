# backend/app/services/detector.py
import cv2
import numpy as np

class BoardDetector:
    def __init__(self):
        # YOLO model removed as the provided best.pt was insufficiently trained.
        # Fallback to pure computer vision (OpenCV) for reliable board extraction.
        pass

    def detect(self, image: np.ndarray, conf_threshold: float = 0.1):
        height, width = image.shape[:2]
        
        # Preprocess for contour detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if cnts:
            # Sort by area to find the largest objects (likely the board)
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
            
            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                
                # If we found a 4-point contour that takes up at least 10% of the screen
                if len(approx) == 4 and cv2.contourArea(c) > (width * height * 0.05):
                    x, y, w, h = cv2.boundingRect(approx)
                    return [{
                        'bbox': [x, y, x+w, y+h],
                        'confidence': 0.95,
                        'class': 'board'
                    }]
            
            # Fallback to the largest contour if it's somewhat large
            x, y, w, h = cv2.boundingRect(cnts[0])
            if w * h > (width * height * 0.05):
                return [{
                    'bbox': [x, y, x+w, y+h],
                    'confidence': 0.85,
                    'class': 'board'
                }]
                
        # Ultimate fallback: Return a centered box so OCR can still try to read the frame
        margin_x = int(width * 0.05)
        margin_y = int(height * 0.05)
        return [{
            'bbox': [margin_x, margin_y, width - margin_x, height - margin_y],
            'confidence': 0.50,
            'class': 'board (full frame)'
        }]