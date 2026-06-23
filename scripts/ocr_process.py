#!/usr/bin/env python3
"""Google Sheets 自動管理スクリプト
- 日付が過ぎたギグを archive に自動移動
- 既存のphoto URLは上書きしない
"""
import sys, json
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

SHEET_ID = __import__('os').environ.get("GOOGLE_SHEET_ID", "")
CREDS_JSON = __import__('os').environ.get("GOOGLE_CREDENTIALS", "")

print("=== Gig Archive Manager ===")

if not SHEET_ID or not CREDS_JSON:
    print("シークレット未設定。スキップ。")
    sys.exit(0)

try:
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.Client(auth=creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_values()
except Exception as e:
    print(f"接続エラー: {e}")
    sys.exit(1)

if len(data) < 2:
    print("データなし。")
    sys.exit(0)

rows = data[1:]
print(f"既存データ: {len(rows)}行")

# 既存photo URLの保存
saved_photos = {}
for i, row in enumerate(rows):
    if len(row) >= 2 and row[0] and row[1]:
        key = (str(row[0]).strip(), str(row[1]).strip().lower())
        saved_photos[key] = row[3] if len(row) > 3 else ""

today = datetime.now()
archived = 0
for i, row in enumerate(rows):
    if len(row) >= 1 and row[0]:
        try:
            gig_date = datetime.strptime(row[0], "%Y-%m-%d")
            if gig_date < today:
                # already archived?
                if len(row) > 4 and row[4].strip() == "past":
                    continue
                # restore photo URL if user had one
                key = (row[0], row[1].strip().lower())
                if key in saved_photos and saved_photos[key]:
                    while len(row) < 4:
                        row.append("")
                    row[3] = saved_photos[key]
                # mark as past
                row.append("past")
                rows[i] = row
                archived += 1
        except ValueError:
            pass

if archived > 0:
    try:
        ws.clear()
        ws.update(values=[["date", "event", "venue", "photo", "link", "type"]], range_name="A1:F1")
        if rows:
            ws.update(values=rows, range_name="A2:F" + str(len(rows) + 1))
        print(f"✓ {archived}行を archive 移動")
    except Exception as e:
        print(f"更新エラー: {e}")
else:
    print("移動するデータなし。")
