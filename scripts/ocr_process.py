#!/usr/bin/env python3
import os, sys, re, json, glob
from datetime import datetime
from pathlib import Path
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials

FLYERS_DIR = Path(__file__).resolve().parent.parent / "flyers"
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")
DRIVE_ID = os.environ.get("DRIVE_FOLDER_ID", "")

# === 1. ENV CHECK ===
print("=== ENV CHECK ===")
sid = SHEET_ID or "NOT SET"
crd = CREDS_JSON or "NOT SET"
drv = DRIVE_ID or "NOT SET"
print(f"  SHEET: {sid[:10]}...")
print(f"  CREDS: {crd[:10]}...")
print(f"  DRIVE: {drv[:10]}...")

# === 2. OCR ===
image_files = glob.glob(str(FLYERS_DIR / "*.{jpg,jpeg,png,JPG,JPEG,PNG}"))
print(f"\n=== FILES: {len(image_files)} ===")

if not image_files:
    print("No images. Exit.")
    sys.exit(0)

# Google Sheets setup
gc = None
if SID := SHEET_ID and CREDS_JSON:
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.Client(auth=creds)
        sh = gc.authorize().open_by_key(SID)
        ws = sh.sheet1
        data = ws.get_all_values()
        existing = data[1:] if data else []
        print(f"  Sheets OK: {len(existing)} rows")
    except Exception as e:
        print(f"  Sheets ERR: {e}")

# Process images
added = []
for img in sorted(image_files):
    fn = os.path.basename(img)
    print(f"\n→ {fn}")
    # OCR
    try:
        client = vision.ImageTextDetector()
        with open(img, "rb") as f:
            resp = client.detect_text(vision.Image(content=f.read()))
        text = resp.text_annotations[0].description if resp.text_annotations else ""
    except Exception as e:
        print(f"  OCR ERR: {e}")
        text = ""
    
    if not text:
        print("  (empty)")
        continue
    
    # Parse date
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    if m:
        date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    else:
        date = ""
    
    # Parse name from filename
    stem = Path(fn).stem
    dm = re.match(r'^(\d{8})', stem)
    name = stem[len(dm[1]):].replace("_", " ").title() if dm else ""
    
    print(f"  date={date} name={name}")
    
    if not date or not name:
        print("  SKIP")
        continue
    
    # Check duplicate
    is_dup = False
    for row in existing or []:
        if len(row) >= 2 and str(row[0]).strip() == date and str(row[1]).strip().lower() == name.lower():
            is_dup = True
            break
    
    if is_dup:
        print("  duplicate")
        continue
    
    # Photo URL
    photo = f"flyers/{fn}"
    if DRIVE_ID:
        photo = f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=sharing"
    
    added.append([date, name, "", photo, ""])

print(f"\n=== ADDED: {len(added)} ===")

# === 3. UPDATE SHEET ===
if gc and added:
    try:
        data.extend(added)
        data.sort(key=lambda r: str(r[0]) if r[0] else "0000", reverse=True)
        ws.clear()
        ws.update("A1:E1", [["date", "event", "venue", "photo", "link"]])
        ws.update("A2:E" + str(len(data) + 1), data)
        print("  Sheet UPDATED!")
    except Exception as e:
        print(f"  Sheet ERR: {e}")
else:
    print("  SKIP (no gc or no added)")

print("=== DONE ===")
