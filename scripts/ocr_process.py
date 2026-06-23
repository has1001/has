#!/usr/bin/env python3
"""
Flyer 画像を OCR してイベント情報を抽出し、Google Sheets に同期する。
"""
import os
import sys
import re
import json
import glob
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
COL_DATE = 0
COL_EVENT = 1
COL_VENUE = 2
COL_PHOTO = 3
COL_LINK = 4

DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")


def get_gc():
    """gspread Client を作成"""
    if not SHEET_ID or not CREDENTIALS_JSON:
        print(f"[ERR] GOOGLE_CREDENTIALS: {'設定' if CREDENTIALS_JSON else '未設定'}")
        print(f"[ERR] GOOGLE_SHEET_ID: {'設定' if SHEET_ID else '未設定'}")
        return None
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.Client(auth=creds)
    except Exception as e:
        print(f"[ERR] 認証エラー: {e}")
        return None


def get_sheets_data(gc):
    """シートデータを取得"""
    if not gc:
        return []
    try:
        sh = gc.authorize().open_by_key(SHEET_ID)
        ws = sh.sheet1
        data = ws.get_all_values()
        print(f"  [OK] シート取得: {len(data)}行")
        return data[1:] if data else []
    except Exception as e:
        print(f"  [ERR] シート取得失敗: {e}")
        return []


def update_sheet(gc, data):
    """シートを更新"""
    if not gc:
        print("[SKIP] クライアント未設定のため更新跳过")
        return True
    try:
        sh = gc.authorize().open_by_key(SHEET_ID)
        ws = sh.sheet1
        data.sort(key=lambda r: str(r[COL_DATE]) if r[COL_DATE] else "0000-00-00", reverse=True)
        ws.clear()
        ws.update("A1:E1", [["date", "event", "venue", "photo", "link"]])
        if data:
            ws.update("A2:E" + str(len(data) + 1), data)
        print(f"  [OK] {len(data)}行を更新")
        return True
    except Exception as e:
        print(f"  [ERR] 更新失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def ocr_image(image_path):
    """Google Cloud Vision API でテキスト抽出"""
    try:
        client = vision.ImageTextDetector()
        with open(image_path, "rb") as f:
            image = vision.Image(content=f.read())
        response = client.detect_text(image=image)
        texts = response.text_annotations
        if texts:
            return texts[0].description
    except Exception as e:
        print(f"  [ERR] OCRエラー: {e}")
    return ""


def extract_event_info(text, filename):
    """OCR テキストから date / name / venue を抽出"""
    info = {"date": "", "name": "", "venue": ""}

    # 日付抽出
    m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    if m:
        info["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    else:
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日?', text)
        if m:
            info["date"] = f"{int(m.group(1))}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        else:
            m = re.search(r'(\d{1,2})月(\d{1,2})日?', text)
            if m:
                y = datetime.now().year
                info["date"] = f"{y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # 会場抽出
    venue_keywords = [
        "woda", "kitsune", "shitamachi", "shelter",
        "bulldog", "electron", "wonder", "cook",
        "rooftop", "naked kitchen", "lobelia",
        "gift", "souterrain", "usagi", "forte",
    ]
    text_lower = text.lower()
    for kw in venue_keywords:
        if kw in text_lower:
            idx = text_lower.index(kw)
            context = text[max(0, idx-40):idx+len(kw)+40].strip()
            parts = context.replace("|", "\n").split("\n")
            for p in parts:
                p = p.strip().rstrip(",、")
                if len(p) > 1 and len(p) < 40:
                    if kw in p.lower():
                        info["venue"] = p
                        break
            if info["venue"]:
                break

    # イベント名
    stem = Path(filename).stem
    date_match = re.match(r'^(\d{8})', stem)
    if date_match:
        name_part = stem[len(date_match[1]):]
        if name_part:
            info["name"] = name_part.replace("_", " ").title()

    if not info["name"]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if 5 < len(line) < 40:
                if not re.search(r'\d{4}', line):
                    is_venue = any(kw in line.lower() for kw in venue_keywords)
                    if not is_venue:
                        info["name"] = line
                        break

    return info


def is_duplicate(sheets_data, date, name):
    for row in sheets_data:
        if not row or len(row) < 2:
            continue
        d = str(row[COL_DATE]).strip()
        n = str(row[COL_EVENT]).strip().lower()
        if d == date and n == name.lower():
            return True
    return False


def main():
    print("=== Flyer OCR Processing ===")
    print(f"SHEET_ID: {'設定' if SHEET_ID else '未設定'}")
    print(f"CREDENTIALS: {'設定' if CREDENTIALS_JSON else '未設定'}")
    print(f"DRIVE_FOLDER_ID: {'設定' if DRIVE_FOLDER_ID else '未設定'}")

    # 画像ファイル取得
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        image_files.extend(glob.glob(str(FLYERS_DIR / ext)))

    if not image_files:
        print("flyer 画像が見つかりません。")
        return

    print(f"画像数: {len(image_files)}")

    gc = get_gc()

    # 既存データ
    sheet_data = get_sheets_data(gc)
    print(f"  既存: {len(sheet_data)}行")

    added = 0
    for img_path in sorted(image_files):
        filename = os.path.basename(img_path)
        print(f"\n→ {filename}")

        # OCR
        text = ocr_image(img_path)
        if not text or len(text.strip()) < 10:
            print("  (テキスト抽出結果が短すぎます)")
            print(f"  OCR結果: '{text}'")
            continue
        print(f"  OCR: {text[:100]}...")

        # 抽出
        info = extract_event_info(text, filename)
        print(f"  date={info['date']} name={info['name']} venue={info['venue']}")

        if not info["date"] or not info["name"]:
            print("  ✗ 抽出失敗")
            continue

        if is_duplicate(sheet_data, info["date"], info["name"]):
            print("  ⊘ 重複")
            continue

        photo_url = f"flyers/{filename}"
        if DRIVE_FOLDER_ID:
            photo_url = f"https://drive.google.com/file/d/{DRIVE_FOLDER_ID}/view?usp=sharing"

        row = [info["date"], info["name"], info["venue"], photo_url, ""]
        sheet_data.append(row)
        added += 1
        print("  ✓ 追加")

    # シート更新
    if added > 0:
        print(f"\n--- {added}件追加 ---")
        update_sheet(gc, sheet_data)
    else:
        print("\n--- 追加データなし ---")


if __name__ == "__main__":
    main()
