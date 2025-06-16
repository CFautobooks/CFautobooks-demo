import os
import tempfile
import pytesseract
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import re

app = FastAPI()

# Simple keyword→category rules
CATEGORY_RULES = {
    "office": "Office Supplies",
    "stationery": "Office Supplies",
    "chair": "Office Furniture",
    "desk": "Office Furniture",
    "fuel": "Travel",
    "taxi": "Travel",
    "restaurant": "Meals",
    "coffee": "Meals",
    "software": "Software Expenses",
    "subscription": "Software Expenses"
}

@app.post("/api/ocr")
async def ocr_and_classify(file: UploadFile = File(...)):
    # Validate content type
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Only PNG/JPEG images supported")

    # Save upload to temp file
    contents = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # Open as image
    try:
        img = Image.open(tmp_path)
    except Exception:
        os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail="Cannot open image")

    # OCR to text
    text = pytesseract.image_to_string(img)
    os.unlink(tmp_path)

    # Parse lines for amounts & descriptions
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(r"\$?([0-9]+(?:\.[0-9]{2})?)", line)
        if not m:
            continue
        amt = float(m.group(1))
        desc = re.sub(r"[^A-Za-z ]", "", line).strip().lower()
        cat = "Uncategorized"
        for kw, c in CATEGORY_RULES.items():
            if kw in desc:
                cat = c
                break
        items.append({
            "description": desc,
            "amount": amt,
            "category": cat,
            "confidence": 0.85,
            "requires_review": (cat == "Uncategorized")
        })

    return JSONResponse(content={"line_items": items})
