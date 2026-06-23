import json, os
from google.oauth2.service_account import Credentials
import gspread

with open("scripts/creds.json") as f:
    creds_info = json.load(f)

creds = Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.Client(auth=creds)

SHEET_ID = "1DYdhlQLTfb_1ISHRvj7h3WLVBy3ddKgSJRaI3XD7F40"
print("Connecting to sheet...")
try:
    # gspread v6+ API
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_values()
    print(f"Connected! {len(data)} rows")
    for i, row in enumerate(data[:5]):
        print(f"  Row {i}: {row}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
