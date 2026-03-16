"""
Board ROI Detector - Kathmandu Municipality Board
==================================================
Detects the blue board and extracts 6 labeled regions:

  1st - Street name box  (ठमेल मार्ग  — large Nepali road name with black border)
  2nd - Kataho code box  (कताहो कोड  — big black-bordered number row)
  3rd - KID row          (KID: 09-294-156-6688)
  4th - Plus code row    (Plus code : 7MV7P896+4R8)
  5th - Nepali address   (काठमाडौं महानगरपालिका, वडा नं २६, ठमेल)
  6th - QR code          (bottom-right QR square)


Usage:
    python board_roi_detector.py --image board.jpg
    python board_roi_detector.py --image board.jpg --save_crops
    python board_roi_detector.py --image board.jpg --output result.jpg --crops_dir my_crops --save_crops
"""

import cv2
import numpy as np
import argparse
import os


# ─────────────────────────────────────────────────────────────────────────────
# ROI layout as (x_frac, y_frac, w_frac, h_frac) of the detected board bbox.
# These fractions are calibrated to the Kathmandu municipality board layout.
# ─────────────────────────────────────────────────────────────────────────────
ROI_FRACTIONS = {
    "1st_street_name":    (0.20, 0.28, 0.65, 0.14),   # ठमेल मार्ग (black-bordered box)
    "2nd_kataho_code":    (0.05, 0.38, 0.92, 0.24),   # कताहो कोड + large Nepali number
    "3rd_KID_row":        (0.35, 0.57, 0.62, 0.08),   # KID: xx-xxx-xxx-xxxx
    "4th_plus_code":      (0.20, 0.64, 0.62, 0.09),   # Plus code : XXXXXXX+XXX
    "5th_nepali_address": (0.20, 0.73, 0.60, 0.17),   # काठमाडौं महानगरपालिका, वडा नं २६, ठमेल
    "6th_QR_code":        (0.80, 0.68, 0.18, 0.22),   # QR code square
}

BOX_COLORS = {
    "1st_street_name":    (0, 0, 255),      # red
    "2nd_kataho_code":    (255, 0, 255),    # magenta
    "3rd_KID_row":        (0, 165, 255),    # orange
    "4th_plus_code":      (255, 255, 0),    # cyan
    "5th_nepali_address": (0, 255, 255),    # yellow
    "6th_QR_code":        (128, 0, 255),    # purple
}


def detect_board(image: np.ndarray):
    """
    Detect the blue municipality board via HSV color segmentation.
    Returns (bx, by, bw, bh) bounding box in image coordinates.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 100, 80])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((15, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No blue board detected. Check image quality / lighting.")

    board_contour = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(board_contour)


def compute_rois(bx, by, bw, bh) -> dict:
    """Convert fractional ROI definitions → absolute pixel (x, y, w, h)."""
    return {
        label: (
            bx + int(bw * xf),
            by + int(bh * yf),
            int(bw * wf),
            int(bh * hf),
        )
        for label, (xf, yf, wf, hf) in ROI_FRACTIONS.items()
    }


def draw_rois(image, bx, by, bw, bh, rois) -> np.ndarray:
    """Return a copy of image with board boundary and ROI boxes drawn."""
    vis = image.copy()
    cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 255, 0), 3)
    cv2.putText(vis, "BOARD", (bx + 6, by + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    for label, (rx, ry, rw, rh) in rois.items():
        color = BOX_COLORS[label]
        cv2.rectangle(vis, (rx, ry), (rx + rw, ry + rh), color, 3)
        cv2.putText(vis, label, (rx + 4, ry - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return vis


def save_crops(image, rois, out_dir):
    """Save each ROI as a separate cropped JPEG."""
    os.makedirs(out_dir, exist_ok=True)
    for label, (rx, ry, rw, rh) in rois.items():
        path = os.path.join(out_dir, f"{label}.jpg")
        cv2.imwrite(path, image[ry:ry + rh, rx:rx + rw])
        print(f"   Saved: {path}")


def process_image(image_path, output_path="annotated_board.jpg",
                    save_crops_flag=False, crops_dir="roi_crops"):
    """Full pipeline. Returns dict of ROI coordinates."""
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w = image.shape[:2]
    print(f"[•] Image: {w}×{h} px")

    bx, by, bw, bh = detect_board(image)
    print(f"[✓] Board: x={bx}, y={by}, w={bw}, h={bh}")

    rois = compute_rois(bx, by, bw, bh)

    print("\n[•] ROI Coordinates  (x, y, w, h):")
    for label, coords in rois.items():
        print(f"   {label:25s} → {coords}")

    vis = draw_rois(image, bx, by, bw, bh, rois)
    cv2.imwrite(output_path, vis)
    print(f"\n[✓] Annotated image  → {output_path}")

    if save_crops_flag:
        print(f"\n[•] Saving crops     → {crops_dir}/")
        save_crops(image, rois, crops_dir)

    return rois


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract 6 ROI regions from Kathmandu municipality board images.")
    parser.add_argument("--image",      required=True,
                        help="Input board image path")
    parser.add_argument("--output",     default="annotated_board.jpg",
                        help="Annotated output image (default: annotated_board.jpg)")
    parser.add_argument("--crops_dir",  default="roi_crops",
                        help="Directory for ROI crops (default: roi_crops)")
    parser.add_argument("--save_crops", action="store_true",
                        help="Save individual ROI crop images")
    args = parser.parse_args()

    process_image(args.image, args.output, args.save_crops, args.crops_dir)
    print("\nDone ✓")