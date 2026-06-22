#!/usr/bin/env python3
"""
Flyer 画像を OCR してイベント情報を抽出し、Google Sheets に同期する。
"""
import os
import sys
import re
import json
import glob
import csv
from datetime import datetime
from pathlib import Path

# Google Cloud Vision API
from google.cloud import vision

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# ── 設定 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FLYERS_DIR = BASE_DIR / "flyers"
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

# Google Sheets 列番号
COL_DATE = 0       # A: 日付
COL_EVENT = 1      # B: イベント名
COL_VENUE = 2      # C: 会場
COL_PHOTO = 3      # D: 画像（画像パスまたはDrive URL）
COL_LINK = 4       # E: リンク（任意）

# Drive フォルダ（「リンクを知っている全員」で公開）
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")


# ── OCR ───────────────────────────────────────────────

def ocr_image(image_path):
    """Google Cloud Vision API でテキスト抽出"""
    client = vision.ImageTextDetector()
    with open(image_path, "rb") as f:
        image = vision.Image(content=f.read())
    response = client.detect_text(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""


def extract_event_info(text, filename):
    """OCR テキストから date / name / venue を抽出"""
    info = {"date": "", "name": "", "venue": ""}

    # ── 日付抽出 ──────────────────────────────────
    # YYYY-MM-DD or YYYY/MM/DD
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    if m:
        info["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    else:
        # 日本語形式: 2026年7月1日
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日?', text)
        if m:
            info["date"] = f"{int(m.group(1))}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        else:
            # 月日みの: 7月1日 (今年と仮定)
            m = re.search(r'(\d{1,2})月(\d{1,2})日?', text)
            if m:
                y = datetime.now().year
                info["date"] = f"{y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # ── 会場抽出 ──────────────────────────────────
    venue_names = [
        "woda", "kitsune", "shitamachi", "shelter",
        "bulldog", "electron", "Wonder", "cook",
        "club earth", "club ...", "rooftop",
        "hayamachi", "naked kitchen", "garret",
        "lobelia", "gift", "live rooster",
        "souterrain", "usagi", "crown",
        "2.5d", "forte", "setter",
    ]
    text_lower = text.lower()
    for name in venue_names:
        if name.lower() in text_lower:
            # 文脈を少し取得
            idx = text_lower.index(name.lower())
            context = text[max(0, idx-30):idx+len(name)+30].strip()
            # 前後の改行で区切る
            parts = re.split(r'[\n|]', context)
            info["venue"] = parts[0].strip().rstrip(",、")
            break

    # ── イベント名 ────────────────────────────────
    # 画像ファイル名から推測: 20260717_elemog.jpeg → "elemog"
    stem = Path(filename).stem
    date_prefix = re.match(r'^\d{8}', stem)
    if date_prefix:
        name_candidate = stem[len(date_prefix[0]):]
        if name_candidate:
            info["name"] = name_candidate.title()

    # 名が空の場合は、OCRテキストから長い行をイベント名とみなす
    if not info["name"]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # 短い日付行や会場名は除外
            if len(line) > 5 and len(line) < 40:
                if not re.search(r'\d{4}', line) and not any(v.lower() in line.lower() for v in venue_names):
                    info["name"] = line
                    break

    return info


def is_duplicate(sheets_data, date, name):
    """既存データと重複チェック"""
    for row in sheets_data:
        d = str(row[COL_DATE]).strip()
        n = str(row[COL_EVENT]).strip().lower()
        if d == date and n == name.lower():
            return True
    return False


# ── Google Sheets ─────────────────────────────────────

def get_sheets_data():
    """シートデータを取得"""
    if not SHEET_ID or not CREDENTIALS_JSON:
        print("  ✗ GOOGLE_SHEET_ID / GOOGLE_CREDENTIALS が必要です")
        return []
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.client(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        data = ws.get_all_values()
        if data:
            return data[1:]  # ヘッダー除外
        return []
    except Exception as e:
        print(f"  ✗ シート取得エラー: {e}")
        return []


def update_sheet(data):
    """シートを更新（日付順ソート＋文字色調整）"""
    if not SHEET_ID or not CREDENTIALS_JSON:
        return
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.client(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        # 日付でソート（新しい順）
        data.sort(key=lambda r: str(r[COL_DATE]), reverse=True)
        ws.clear()
        # ヘッダー
        ws.update("A1:E1", [["date", "event", "venue", "photo", "link"]])
        # データ
        if data:
            ws.update("A2:E" + str(len(data) + 1), data)
    except Exception as e:
        print(f"  ✗ シート更新エラー: {e}")


# ── メイン ────────────────────────────────────────────

def main():
    print("=== Flyer OCR Processing ===")
    print(f"FLYERS_DIR: {FLYERS_DIR}")
    print(f"SHEET_ID: {SHEET_ID[:10]}..." if SHEET_ID else "SHEET_ID: (not set)")

    # 画像ファイル取得
    image_files = glob.glob(str(FLYERS_DIR / "*.jpg")) + \
                  glob.glob(str(FLYERS_DIR / "*.jpeg")) + \
                  glob.glob(str(FLYERS_DIR / "*.png")) + \
                  glob.glob(str(FLYERS_DIR / "*.JPG")) + \
                  glob.glob(str(FLYERS_DIR / "*.JPEG")) + \
                  glob.glob(str(FLYERS_DIR / "*.PNG"))

    if not image_files:
        print("flyer 画像が見つかりません。")
        return

    # 既存シートデータを取得
    sheet_data = get_sheets_data()

    added = 0
    for img_path in sorted(image_files):
        filename = os.path.basename(img_path)
        print(f"\n→ {filename}")

        # OCR
        text = ocr_image(img_path)
        if not text or len(text.strip()) < 10:
            print("  (テキスト抽出結果が短すぎます)")
            continue
        print(f"  OCR: {text[:100]}...")

        # イベント情報抽出
        info = extract_event_info(text, filename)
        print(f"  抽出: date={info['date']}, name={info['name']}, venue={info['venue']}")

        # 最低限、日付と名があるかチェック
        if not info["date"] or not info["name"]:
            print("  ✗ 完全な情報抽出に失敗しました")
            continue

        # 重複チェック
        if is_duplicate(sheet_data, info["date"], info["name"]):
            print("  ⊘ 重複データです")
            continue

        # photo 列には画像ファイル名を保存（後でDrive URLに変換可能）
        photo_url = f"flyers/{filename}"
        if DRIVE_FOLDER_ID:
            photo_url = f"https://drive.google.com/file/d/{DRIVE_FOLDER_ID}/view?usp=sharing"

        row = [info["date"], info["name"], info["venue"], photo_url, ""]
        sheet_data.append(row)
        added += 1

    # シート更新
    if added > 0:
        print(f"\n---")
        print(f"{added}件追加 → シート更新中...")
        update_sheet(sheet_data)
        print("完了！")
    else:
        print("\n---")
        print("追加するデータはありません。")


if __name__ == "__main__":
    main()
