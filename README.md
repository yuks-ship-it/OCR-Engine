# 🏙️ Board OCR System

A real-time OCR system that reads text from Kathmandu Municipality
address boards using a live camera, OpenCV, and EasyOCR.

---

## 📸 What It Reads

Given a photo of a blue municipality board, the system extracts:

| Field | Example Output |
|---|---|
| मार्ग (Street Name) | मनेश्वरी मार्ग |
| Kataho Code | ०९ लक्ष मुना २७२० |
| KID Number | 09-294-156-6688 |
| Plus Code | 7MV7P8J7+Q8X |
| Ward No | वडा नं २६ |
| Location | ठमेल |
| QR Code | (decoded automatically) |

---

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start the server
cd backend
uvicorn app.main:app --reload

# 4. Open browser
# http://localhost:8000
```

> ⚠️ First startup takes 30–60 seconds — EasyOCR downloads language models.
> After first run it starts instantly.

---

## 🗂️ Project Structure

```
ocr_system/
├── backend/
│   ├── app/
│   │   ├── main.py            ← FastAPI app entry point
│   │   ├── config.py          ← Settings (OCR languages, paths)
│   │   ├── api/
│   │   │   └── routes.py      ← API endpoints
│   │   └── services/
│   │       ├── detector.py        ← Board detection
│   │       ├── ocr_engine.py      ← Text recognition
│   │       ├── qr_reader.py       ← QR code reading
│   │       ├── field_parser.py    ← Field extraction
│   │       └── roi_extractor.py   ← Region of interest extraction
│   └── requirements.txt
│
└── frontend/
    ├── index.html             ← Camera UI
    ├── script.js              ← Camera + API logic
    └── style.css              ← Styling
```

---

## 🔧 OCR Engine — How It Works

The OCR engine is the core of this system. It processes each camera
frame through a 5-step pipeline:

```
Camera Frame
     │
     ▼
Step 1: Board Detection      (detector.py)
     │
     ▼
Step 2: ROI Extraction       (roi_extractor.py)
     │
     ▼
Step 3: Text Recognition     (ocr_engine.py)
     │
     ▼
Step 4: QR Code Reading      (qr_reader.py)
     │
     ▼
Step 5: Field Parsing        (field_parser.py)
     │
     ▼
JSON Response to Frontend
```

---

### Step 1 — Board Detection (`detector.py`)

**Purpose:** Find the blue board inside the camera image.

The detector uses HSV (Hue-Saturation-Value) color space to isolate
the blue color of the municipality board. Unlike RGB, HSV is much more
reliable for detecting specific colors under different lighting conditions.

**How it works:**

```
Input Image (BGR)
       │
       ▼
Convert to HSV color space
       │
       ▼
Apply blue color mask
  lower_blue = [90,  80,  60]
  upper_blue = [135, 255, 255]
       │
       ▼
Morphological cleanup
  (remove noise, fill gaps)
       │
       ▼
Find contours in mask
       │
       ▼
Pick largest blue contour
       │
       ▼
Get bounding box (x1, y1, x2, y2)
       │
       ▼
Try perspective correction (deskew)
if board is tilted in photo
       │
       ▼
Return board crop image
```

If blue color detection fails (unusual lighting), it falls back to
edge detection using Canny + adaptive thresholding. If that also fails,
it uses the full frame as the board crop.

**Output:**
```python
{
    "bbox":       [167, 143, 596, 480],   # board location in full image
    "confidence": 0.95,                   # detection confidence
    "crop":       <numpy array>           # cropped board image
}
```

---

### Step 2 — ROI Extraction (`roi_extractor.py`)

**Purpose:** Divide the board crop into 6 named regions.

Instead of running OCR on the whole board at once, the system cuts it
into 6 specific regions. This improves accuracy because each region
contains only the relevant text.

**The 6 regions and their positions (as fractions of board size):**

| Region | X start | Y start | Width | Height |
|---|---|---|---|---|
| street_name | 20% | 28% | 65% | 14% |
| kataho_code | 5% | 38% | 92% | 24% |
| kid_row | 35% | 57% | 62% | 8% |
| plus_code | 20% | 64% | 62% | 9% |
| nepali_address | 20% | 73% | 60% | 17% |
| qr_code | 80% | 68% | 18% | 22% |

**Output for each region:**
```python
{
    "x": 85, "y": 94, "w": 278, "h": 47,   # relative to board crop
    "abs_x": 252, "abs_y": 237,             # in full image
    "abs_x2": 530, "abs_y2": 284
}
```

---

### Step 3 — Text Recognition (`ocr_engine.py`)

**Purpose:** Read the text from each ROI region.

This is the main OCR step. It uses **EasyOCR** which supports both
Nepali (Devanagari script) and English in the same image.

**Languages loaded:**
```python
OCR_LANGUAGES = ["ne", "en"]   # Nepali + English
```

**Preprocessing pipeline:**

Because board photos can have glare, shadows, or uneven lighting,
the engine tries 4 different preprocessing variants and picks the one
with the highest confidence score.

```
Region crop image
       │
       ▼
Convert to grayscale
       │
       ├── Variant 1: CLAHE enhancement + sharpen
       │     Good for low contrast / dark boards
       │
       ├── Variant 2: Otsu thresholding
       │     Good for high contrast boards
       │
       ├── Variant 3: Adaptive thresholding
       │     Good for uneven / shadow lighting
       │
       └── Variant 4: Inverted (white text on dark)
             Good for light text on dark background
                   │
                   ▼
             Run EasyOCR on all 4 variants
                   │
                   ▼
             Pick variant with highest
             average confidence score
                   │
                   ▼
             Return text + confidence
```

**Upscaling for small text:**
If the region image is smaller than 800px, it is scaled up 2x before
OCR. This significantly improves accuracy for small text like the
KID number row.

**Output:**
```python
{
    "text":           "मनेश्वरी मार्ग",
    "avg_confidence": 0.87,
    "words": [
        {"text": "मनेश्वरी", "confidence": 0.91},
        {"text": "मार्ग",   "confidence": 0.83}
    ]
}
```

---

### Step 4 — QR Code Reading (`qr_reader.py`)

**Purpose:** Decode the QR code in the bottom-right of the board.

The QR reader uses OpenCV's built-in QR detector on the dedicated
`qr_code` region crop. Using just the QR region (instead of the full
board) makes detection much faster and more reliable.

**Output:**
```python
["https://maps.google.com/?q=..."]   # decoded QR content
```

---

### Step 5 — Field Parsing (`field_parser.py`)

**Purpose:** Extract structured fields from the raw OCR text.

EasyOCR returns raw text strings. The field parser uses regex patterns
to identify and extract each specific field.

**Nepali digit normalization:**

OCR often reads Nepali digits (०१२३४५६७८९) as a mix of Nepali
and English. The parser converts all Nepali digits to English before
matching:

```python
NEP_TO_ENG = str.maketrans('०१२३४५६७८९', '0123456789')
```

**Parsing rules for each field:**

**मार्ग (Street Name):**
Matches one or two Nepali words followed by मार्ग.
```
Pattern: [\u0900-\u097F]+ [\u0900-\u097F]* मार्ग
Example: "मनेश्वरी मार्ग" → मनेश्वरी मार्ग
```

**Kataho Code:**
Matches lines starting with 09 or ०९ followed by Nepali words and a 4-digit number.
```
Pattern: (09|०९) + Nepali words + 4 digits
Example: "०९ लक्ष मुना २७२०" → 09 लक्ष मुना 2720
```

**KID Number:**
Matches the KID label followed by the number pattern.
```
Pattern: KID[\s:]+ digits with dashes
Example: "KID: 09-294-156-6688" → 09-294-156-6688
```

**Plus Code:**
Matches the standard Open Location Code format.
```
Pattern: [A-Z0-9]{4,8}+[A-Z0-9]{2,4}
Example: "Plus code: 7MV7P8J7+Q8X" → 7MV7P8J7+Q8X
```

**Ward Number:**
Matches महानगरपालिका followed by वडा and a number.
```
Pattern: महानगरपालिका + वडा + digits
Example: "काठमाडौं महानगरपालिका, वडा नं २६" → वडा नं 26
```

**Location:**
Checks against a known list of Kathmandu Valley location names
(ठमेल, बौद्ध, गोङ्गबु, बानेश्वर, etc.).

**Output:**
```python
{
    "marga":        "मनेश्वरी मार्ग",
    "kataho_code":  "09 लक्ष मुना 2720",
    "kid":          "09-294-156-6688",
    "plus_code":    "7MV7P8J7+Q8X",
    "ward_no":      "वडा नं 26",
    "location":     "ठमेल"
}
```

---

## 📡 API

### POST `/api/process` — Full OCR Pipeline

Send a board image, get all extracted fields back.

**Request:**
```
POST /api/process
Content-Type: multipart/form-data
file: <image>
```

**Response:**
```json
{
  "success": true,
  "total_detections": 1,
  "detections": [
    {
      "bbox": [167, 143, 596, 480],
      "detection_confidence": 0.95,
      "class": "board",
      "ocr_text": "मनेश्वरी मार्ग\n०९ लक्ष मुना २७२०\nPlus code : 7MV7P8J7+Q8X",
      "ocr_confidence": 0.85,
      "parsed_fields": {
        "marga":        "मनेश्वरी मार्ग",
        "kataho_code":  "09 लक्ष मुना 2720",
        "kid":          "09-294-156-6688",
        "plus_code":    "7MV7P8J7+Q8X",
        "ward_no":      "वडा नं 26",
        "location":     "ठमेल"
      },
      "roi_coordinates": {
        "street_name":    {"x": 85,  "y": 94,  "w": 278, "h": 47},
        "kataho_code":    {"x": 21,  "y": 128, "w": 394, "h": 80},
        "kid_row":        {"x": 150, "y": 192, "w": 265, "h": 26},
        "plus_code":      {"x": 85,  "y": 215, "w": 265, "h": 30},
        "nepali_address": {"x": 85,  "y": 246, "w": 257, "h": 57},
        "qr_code":        {"x": 343, "y": 229, "w": 77,  "h": 74}
      },
      "qr_data": [],
      "cropped_image": "<base64 jpg>"
    }
  ],
  "annotated_image": "<base64 jpg>"
}
```

### GET `/api/health`
```json
{ "status": "ok" }
```

### GET `/docs`
Interactive Swagger UI — test all endpoints from the browser.

---

## 🖥️ Frontend

The frontend is a single HTML page served by the FastAPI backend.
No separate frontend server is needed.

**`index.html`** — UI layout with camera panel and results panel.

**`script.js`** — handles everything:
- Opens webcam using `getUserMedia`
- Captures frame on button click
- Sends frame to `/api/process`
- Draws green board bounding box on canvas
- Draws 6 colored ROI boxes on canvas
- Displays parsed fields in the results panel

**`style.css`** — dark theme styling for the UI.

**Controls in the browser:**

| Button | Action |
|---|---|
| Manual Capture | Scan once |
| Start Auto Scan | Scan every 1.5 seconds continuously |
| Stop Auto Scan | Stop continuous scanning |

---

## ❓ Common Issues

| Problem | Fix |
|---|---|
| Camera access denied | Allow camera in browser Settings → Camera |
| Slow first startup | Normal — EasyOCR downloading models |
| No board detected | Ensure good lighting, full board visible |
| Fields showing — | Improve lighting or adjust field_parser regex |
| ModuleNotFoundError | Run `pip install -r requirements.txt` |
| Port already in use | Use `uvicorn app.main:app --port 8002` |

---

## 📐 About ROI and How Coordinates Are Calculated

ROI stands for **Region of Interest**. It is a specific rectangular
area inside the detected board that contains one particular piece of
information.

Instead of running OCR on the entire board image at once, the system
divides the board into 6 smaller regions and runs OCR on each one
separately. This approach gives better accuracy because each region
contains only its own text with no interference from other fields.

**How the coordinates are calculated:**

Each ROI region is defined as a set of fractions — a percentage of
the board's total width and height. This means the regions scale
automatically no matter how close or far the camera is from the board.

```
board_crop size = width: 429px, height: 337px

street_name region fractions:
    x_frac = 0.20   →   x = 429 × 0.20 = 85px
    y_frac = 0.28   →   y = 337 × 0.28 = 94px
    w_frac = 0.65   →   w = 429 × 0.65 = 278px
    h_frac = 0.14   →   h = 337 × 0.14 = 47px
```

These are the **relative coordinates** — the position inside the
board crop image.

To get the position in the **full camera image**, the board's own
position is added:

```
board_bbox = [167, 143, 596, 480]
board origin = (x1=167, y1=143)

street_name in full image:
    abs_x  = 167 + 85  = 252
    abs_y  = 143 + 94  = 237
    abs_x2 = 252 + 278 = 530
    abs_y2 = 237 + 47  = 284
```

The frontend uses these absolute coordinates to draw colored boxes
directly on the live camera canvas, showing exactly which part of
the board each field was read from.

**The 6 ROI regions laid out on the board:**

```
┌─────────────────────────────────────────┐  ▲
│           मार्ग  (street_name)          │  │ 28%–42%
├─────────────────────────────────────────┤  │
│        कताहो कोड (kataho_code)          │  │ 38%–62%
│        ०९ लक्ष मुना २७२०               │  │
├──────────────────────────────┬──────────┤  │
│  KID: 09-xxx-xxx-xxxx        │          │  │ 57%–65%
├──────────────────────────────┤  QR Code │  │ 68%–90%
│  Plus code: XXXXXXX+XXX      │          │  │ 64%–73%
├──────────────────────────────┤          │  │
│  काठमाडौं महानगरपालिका      │          │  │ 73%–90%
│  वडा नं २६, ठमेल            │          │  ▼
└──────────────────────────────┴──────────┘
 ◄────── 5% ──────────────── 92% ────────►
```

**Why fractions instead of fixed pixels?**

If fixed pixel values were used, the ROI regions would only work for
images taken at one specific distance. Using fractions means the same
definition works whether the board fills the whole frame or is just
a small part of a wide-angle shot.

---

## 👨‍💻 Author

Yukesh Dhakal