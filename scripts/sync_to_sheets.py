#!/usr/bin/env python3
"""
gigs.md からパースしたギグ情報を Google Sheets に同期する。
"""
import json
import os
import sys
import re

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from datetime import datetime
except ImportError:
    print("gspread and google-auth required. Install: pip install gspread google-auth")
    sys.exit(1)

def parse_date_for_sheet(date_str):
    """日付文字列をGoogle Sheets形式に変換"""
    date_str = date_str.strip()
    # YYYY-MM-DD → YYYY-MM-DD (そのまま)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    # YYYY/MM/DD → YYYY-MM-DD
    m = re.match(r'^(\d{4})/(\d{2})/(\d{2})$', date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 2026年7月1日 → YYYY-MM-DD
    m = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日?$', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return date_str

def sync_to_sheets():
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS')

    if not sheet_id or not credentials_json:
        print("GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS env vars required.")
        sys.exit(1)

    # Parse gigs.md
    md_path = os.path.join(os.path.dirname(__file__), '..', 'gigs.md')
    subprocess_result = os.popen(f'python {os.path.join(os.path.dirname(__file__), "parse_gigs_md.py")}')
    gigs_data = json.loads(subprocess_result.read())

    # Connect to Google Sheets
    creds = Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    gc = gspread.client(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1  # 最初のシート

    # Read existing data (skip header)
    existing = ws.get_all_values()

    # Build sets for comparison
    existing_keys = set()
    for row in existing[1:]:
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            # Key is (date, name)
            existing_keys.add((row[0].strip(), row[1].strip()))

    new_rows = []
    for item in gigs_data['upcoming'] + gigs_data['past']:
        key = (item['date'], item['name'])
        if key in existing_keys:
            continue  # Already exists

        new_rows.append([
            parse_date_for_sheet(item['date']),
            item['name'],
            item['venue'],
            item.get('photo', ''),
            item.get('link', '')
        ])

    if new_rows:
        # Find first empty row
        last_row = len(existing)
        ws.append_rows(new_rows, value_input_option='RAW', insert_inherit=True)
        print(f"Added {len(new_rows)} new gig(s) to Google Sheets.")
    else:
        print("No new gigs to add.")

if __name__ == '__main__':
    sync_to_sheets()
