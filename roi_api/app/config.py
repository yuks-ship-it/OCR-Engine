# roi_api/app/config.py

# ROI region fractions (x, y, w, h) of board bounding box
ROI_FRACTIONS = {
    "street_name":    (0.20, 0.28, 0.65, 0.14),
    "kataho_code":    (0.05, 0.38, 0.92, 0.24),
    "kid_row":        (0.35, 0.57, 0.62, 0.08),
    "plus_code":      (0.20, 0.64, 0.62, 0.09),
    "nepali_address": (0.20, 0.73, 0.60, 0.17),
    "qr_code":        (0.80, 0.68, 0.18, 0.22),
}

# Human-readable labels
ROI_LABELS = {
    "street_name":    "Street Name (मार्ग)",
    "kataho_code":    "Kataho Code (कताहो कोड)",
    "kid_row":        "KID Number",
    "plus_code":      "Plus Code",
    "nepali_address": "Nepali Address (काठमाडौं महानगरपालिका)",
    "qr_code":        "QR Code",
}

# Colors for drawing (BGR)
ROI_COLORS = {
    "street_name":    (0,   0,   255),
    "kataho_code":    (255, 0,   255),
    "kid_row":        (0,   165, 255),
    "plus_code":      (255, 255, 0  ),
    "nepali_address": (0,   255, 255),
    "qr_code":        (128, 0,   255),
}