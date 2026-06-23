#!/usr/bin/env python3
"""Google Sheets 自動管理スクリプト
※日付が過ぎたギグを archive に自動移動するだけのシンプルなスクリプト
"""
import sys, json, re
from google.oauth2.service_account import Credentials
import gspread

SHEET_ID = __import__('os').environ.get("GOOGLE_SHEET_ID", "")
CREDS_JSON = __import__('os').environ.get("GOOGLE_CREDENTIALS", "")

print("=== Gig Archive Manager ===")

if not SHEET_ID or not CREDS_JSON:
    print("シークレット未設定。スキップ。")
    sys.exit(0)

# Sheets 接続
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

# ヘッダー除外
rows = data[1:]
print(f"既存データ: {len(rows)}行")

# 日付判定
from datetime import datetime
today = datetime.now()

archived = 0
for i, row in enumerate(rows):
    if len(row) >= 1 and row[0]:
        try:
            gig_date = datetime.strptime(row[0], "%Y-%m-%d")
            if gig_date < today:
                # 既に past としてマーク済みならスキップ
                if len(row) > 4 and row[4].strip() == "past":
                    continue
                # past マーク
                row.append("past")
                rows[i] = row
                archived += 1
        except ValueError:
            pass

# 更新
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
