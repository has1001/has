import json, os, re
from pathlib import Path
from google.cloud import vision
from google.oauth2.service_account import Credentials
import gspread

with open("scripts/creds.json") as f:
    creds_info = json.load(f)
creds = Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.Client(auth=creds)

SHEET_ID = "1DYdhlQLTfb_1ISHRvj7h3WLVBy3ddKgSJRaI3XD7F40"
DRIVE_ID = "1ijTwWY13U9cnxE4SwCoFo4tCkz-k64yX"
FLYERS_DIR = Path("/Users/has/has/flyers")

sh = gc.open_by_key(SHEET_ID)
ws = sh.sheet1
data = ws.get_all_values()

# Get images
images = []
for f in os.listdir(FLYERS_DIR):
    if f.endswith(('.jpg', '.jpeg', '.png')):
        images.append(str(FLYERS_DIR / f))
print(f"Images: {len(images)}")

# Vision API with credentials
vision_creds = Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
client = vision.ImageAnnotatorClient(credentials=vision_creds)

for img_path in sorted(images):
    fn = os.path.basename(img_path)
    print(f"\n→ {fn}")
    
    try:
        with open(img_path, "rb") as f:
            image = vision.Image(content=f.read())
        response = client.text_detection(image=image)
        texts = response.text_annotations
        text = texts[0].description if texts else ""
    except Exception as e:
        print(f"  ERROR: {e}")
        continue
    
    print(f"  OCR: {text[:200]}")
    
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
    
    stem = Path(fn).stem
    dm = re.match(r'^(\d{8})', stem)
    name = stem[len(dm[1]):].replace("_", " ").title() if dm else ""
    
    print(f"  date={date} name={name}")
    
    photo = f"flyers/{fn}"
    if DRIVE_ID:
        photo = f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=sharing"
    
    data.append([date, name, "", photo, ""])
    print("  ✓")

# Write
ws.clear()
ws.update(values=[["date", "event", "venue", "photo", "link"]], range_name="A1:E1")
if data:
    ws.update(values=data[1:], range_name="A2:E" + str(len(data)))
print(f"\n✓ Updated! {len(data)} rows")
