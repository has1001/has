#!/usr/bin/env python3
"""Google Sheets 自動管理スクリプト
- 日付が過ぎたギグを archive に自動移動
- 既存データは上書きしない（安全な追記モード）
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

rows = data[1:]  # ヘッダー除外
print(f"既存データ: {len(rows)}行")

today = datetime.now()
archived = 0

# アーカイズ処理
for i, row in enumerate(rows):
    # ヘッダー除外済みの行が空ならスキップ
    if not row or not row[0]:
        continue
    
    # 日付チェック
    try:
        gig_date = datetime.strptime(row[0].strip(), "%Y-%m-%d")
        past = gig_date < today
        
        # まだ past タグがないかつ過去の日付
        if past and (not row or len(row) < 5 or row[4].strip() != "past"):
            # 必要に応じて列を確保
            while len(row) < 5:
                row.append("")
            row[4] = "past"
            rows[i] = row
            archived += 1
    except ValueError:
        # 日付形式エラーは無視
        pass

# 更新処理
if archived > 0:
    try:
        # clear + 全体書き込み
        ws.clear()
        ws.update(values=[["date", "event", "venue", "photo", "link", "type"]], range_name="A1:F1")
        if rows:
            ws.update(values=rows, range_name="A2:F" + str(len(rows) + 1))
        print(f"✓ {archived}行を archive 移動")
    except Exception as e:
        print(f"更新エラー: {e}")
else:
    print("移動するデータなし。")
