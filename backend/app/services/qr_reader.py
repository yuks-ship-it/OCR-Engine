# backend/app/services/qr_reader.py
import cv2
from pyzbar.pyzbar import decode

class QRReader:
    def read_qr(self, image):
        """
        Detect and decode QR codes in the image.
        Returns a list of decoded strings.
        """
        decoded_objects = decode(image)
        qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]
        return qr_data