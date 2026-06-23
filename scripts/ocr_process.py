#!/usr/bin/env python3
"""Flyer → OCR → Google Sheets"""
import os, sys, re, json
from pathlib import Path
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials

FLYERS_DIR = Path(__file__).resolve().parent.parent / "flyers"
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")

# === 1. ENV CHECK ===
print("Step 1: ENV CHECK")
print(f"  SHEET_ID: {'SET ✓' if SHEET_ID else '✗ NOT SET'}")
print(f"  CREDS:    {'SET ✓' if CREDS_JSON else '✗ NOT SET'}")
print(f"  DRIVE:    {'SET ✓' if DRIVE_FOLDER_ID else '✗ NOT SET'}")

if not SHEET_ID or not CREDS_JSON:
    print("\nERROR: シークレット未設定です。")
    sys.exit(1)

# === 2. FILES ===
print(f"\nStep 2: FILES ({FLYERS_DIR})")
images = []
for f in os.listdir(FLYERS_DIR):
    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
        images.append(str(FLYERS_DIR / f))
print(f"  {len(images)} images")
if not images:
    print("  No images.")
    sys.exit(0)

# === 3. Google Sheets ===
print("\nStep 3: Google Sheets connect")
try:
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.Client(auth=creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_values()
    existing = data[1:] if data else []
    print(f"  ✓ {len(existing)} rows")
except Exception as e:
    print(f"  ✗ ERROR: {e}")
    sys.exit(1)

# === 4. OCR ===
print("\nStep 4: OCR")
try:
    creds_vision = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = vision.ImageAnnotatorClient(credentials=creds_vision)
except Exception as e:
    print(f"  ✗ OCR ERROR: {e}")
    sys.exit(1)

added = []
for img_path in sorted(images):
    fn = os.path.basename(img_path)
    print(f"  → {fn}")
    try:
        with open(img_path, "rb") as f:
            image = vision.Image(content=f.read())
        response = client.text_detection(image=image)
        texts = response.text_annotations
        text = texts[0].description if texts else ""
    except Exception as e:
        print(f"    OCR ERROR: {e}")
        continue

    if len(text.strip()) < 10:
        print(f"    (too short)")
        continue

    # Parse date
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""

    # Parse name from filename
    stem = Path(fn).stem
    dm = re.match(r'^(\d{8})', stem)
    name = stem[len(dm[1]):].replace("_", " ").title() if dm else ""

    # Parse venue
    venue = ""
    venue_kw = ["woda", "kitsune", "shitamachi", "shelter", "bulldog"]
    for kw in venue_kw:
        if kw in text.lower():
            idx = text.lower().index(kw)
            ctx = text[max(0, idx-30):idx+len(kw)+30].strip()
            for p in ctx.split("\n"):
                p = p.strip().rstrip(",、")
                if len(p) > 1 and len(p) < 40 and kw in p.lower():
                    venue = p
                    break
            if venue:
                break

    print(f"    date={date} name={name} venue={venue}")

    if not date or not name:
        print(f"    SKIP")
        continue

    # Duplicate check
    is_dup = False
    for row in existing:
        if len(row) >= 2:
            d = str(row[0]).strip()
            n = str(row[1]).strip().lower()
            if d == date and n == name.lower():
                is_dup = True
                break
    if is_dup:
        print(f"    duplicate")
        continue

    # Photo URL - user manually entered, or use folder as fallback
    photo = f"flyers/{fn}"
    if DRIVE_FOLDER_ID:
        photo = f"https://drive.google.com/file/d/{DRIVE_FOLDER_ID}/view?usp=sharing"

    added.append([date, name, venue, photo, ""])
    print(f"    ✓")

print(f"\nStep 5: UPDATE ({len(added)} new)")
if added:
    try:
        data.extend(added)
        data.sort(key=lambda r: str(r[0]) if r[0] else "0000", reverse=True)
        ws.clear()
        ws.update(values=[["date", "event", "venue", "photo", "link"]], range_name="A1:E1")
        if data:
            ws.update(values=data[1:], range_name="A2:E" + str(len(data)))
        print("  ✓ Sheet UPDATED!")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  SKIP (no new)")

print("\nStep 6: VERIFY")
try:
    fresh = ws.get_all_values()
    print(f"  Sheet now: {len(fresh)} rows")
    for i, row in enumerate(fresh[:5]):
        print(f"    Row {i}: {row}")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

print("\n=== DONE ===")
