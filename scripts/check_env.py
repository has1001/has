import os
print("=== ENV CHECK ===")
sid = os.environ.get("GOOGLE_SHEET_ID", "")
creds = os.environ.get("GOOGLE_CREDENTIALS", "")
drive = os.environ.get("DRIVE_FOLDER_ID", "")
print(f"GOOGLE_SHEET_ID: {sid[:6] if sid else 'NOT SET'}...")
print(f"GOOGLE_CREDENTIALS: {creds[:6] if creds else 'NOT SET'}...")
print(f"DRIVE_FOLDER_ID: {drive[:6] if drive else 'NOT SET'}...")
