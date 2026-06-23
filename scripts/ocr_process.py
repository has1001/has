#!/usr/bin/env python3
"""Flyer → OCR → Google Sheets"""
import os, sys, re, json, glob
from pathlib import Path
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials

FLYERS_DIR = Path(__file__).resolve().parent.parent / "flyers"
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")
DRIVE_ID = os.environ.get("DRIVE_FOLDER_ID", "")

print("Step 1: ENV CHECK")
print(f"  SHEET_ID: {'SET ✓' if SHEET_ID else '✗ NOT SET'}")
print(f"  CREDS:    {'SET ✓' if CREDS_JSON else '✗ NOT SET'}")
print(f"  DRIVE:    {'SET ✓' if DRIVE_ID else '✗ NOT SET'}")

if not SHEET_ID or not CREDS_JSON:
    print("\nERROR: シークレット未設定です。GitHub Settings → Secrets に登録してください。")
    sys.exit(1)

print(f"\nStep 2: FILES ({FLYERS_DIR})")
images = []
for f in os.listdir(FLYERS_DIR):
    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
        images.append(str(FLYERS_DIR / f))
print(f"  {len(images)} images found")
if not images:
    print("  No images. Exit.")
    sys.exit(0)

print("\nStep 3: Google Sheets connect")
try:
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.Client(auth=creds)
    sh = gc.authorize().open_by_key(SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_values()
    existing = data[1:] if data else []
    print(f"  Connected! {len(existing)} rows existing")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

print("\nStep 4: OCR")
added = []
for img_path in sorted(images):
    fn = os.path.basename(img_path)
    print(f"  → {fn}")
    try:
        client = vision.ImageTextDetector()
        with open(img_path, "rb") as f:
            image = vision.Image(content=f.read())
        response = client.detect_text(image=image)
        texts = response.text_annotations
        text = texts[0].description if texts else ""
    except Exception as e:
        print(f"    OCR ERROR: {e}")
        continue
    
    if len(text.strip()) < 10:
        print(f"    (too short: {len(text)} chars)")
        continue
    
    print(f"    OCR: {text[:60]}...")
    
    # Parse date
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
    
    # Parse name
    stem = Path(fn).stem
    dm = re.match(r'^(\d{8})', stem)
    name = stem[len(dm[1]):].replace("_", " ").title() if dm else ""
    
    print(f"    date={date} name={name}")
    
    if not date or not name:
        print("    SKIP (missing date/name)")
        continue
    
    # Check duplicate
    is_dup = False
    for row in existing:
        if len(row) >= 2:
            d = str(row[0]).strip()
            n = str(row[1]).strip().lower()
            if d == date and n == name.lower():
                is_dup = True
                break
    
    if is_dup:
        print("    SKIP (duplicate)")
        continue
    
    photo = f"flyers/{fn}"
    if DRIVE_ID:
        photo = f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=sharing"
    
    added.append([date, name, "", photo, ""])
    print("    ✓")

print(f"\nStep 5: UPDATE ({len(added)} new)")
if added:
    try:
        data.extend(added)
        data.sort(key=lambda r: str(r[0]) if r[0] else "0000", reverse=True)
        ws.clear()
        ws.update("A1:E1", [["date", "event", "venue", "photo", "link"]])
        ws.update("A2:E" + str(len(data) + 1), data)
        print("  ✓ Sheet UPDATED!")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  SKIP (no new data)")

print("\nStep 6: VERIFY")
try:
    fresh = ws.get_all_values()
    print(f"  Sheet now has {len(fresh)} rows")
    for i, row in enumerate(fresh[:5]):
        print(f"    Row {i}: {row}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== COMPLETE ===")
