#!/usr/bin/env python3
"""
Flyer画像をOCRで解析し、イベント情報を抽出する。
Google Cloud Vision API を使用。
抽出結果を gigs.md に追記。
"""
import os
import sys
import json
import re
import glob

try:
    from google.cloud import vision
except ImportError:
    print("google-cloud-vision required. Install: pip install google-cloud-vision")
    sys.exit(1)

def ocr_image(image_path):
    """Google Cloud Vision API で画像からテキストを抽出"""
    client = vision.ImageTextDetector()
    
    with open(image_path, 'rb') as f:
        image_content = f.read()
    
    image = vision.Image(content=image_content)
    response = client.detect_text(image=image)
    texts = response.text_annotations
    
    if not texts or len(texts) < 2:
        return None
    
    # 全体のテキストを取得
    full_text = texts[0].description
    return full_text

def extract_event_info(text):
    """OCR結果からイベント名・日付・会場を抽出"""
    info = {
        'name': '',
        'date': '',
        'venue': ''
    }
    
    # 日付パターン (YYYY-MM-DD, YYYY/MM/DD, 2026年7月1日, 7月1日)
    date_patterns = [
        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',
        r'(\d{4})年(\d{1,2})月(\d{1,2})日?',
        r'(\d{1,2})月(\d{1,2})日?',
    ]
    
    for pattern in date_patterns:
        m = re.search(pattern, text)
        if m:
            if len(m.groups()) == 3 and m.group(1).isdigit():
                if len(m.group(1)) == 4:
                    # Full date with year
                    info['date'] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                else:
                    # Day/Month only
                    info['date'] = f"{int(m.group(1))}月{int(m.group(2))}日"
            elif len(m.groups()) == 2:
                info['date'] = f"{int(m.group(1))}月{int(m.group(2))}日"
            break
    
    # 会場キーワードから抽出
    venue_patterns = [
        r'(?:会場| venue |LIVE|BAR|CLUB|HALL|SQUARE)\s*[:：]?\s*([^\n,|]+)',
        r'(?:woda|kitsune|shitamachi|cb|shelter|bulldog|electron| WONDER|[Ww]onder|COOK|UTY)',
    ]
    
    for pattern in venue_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if ':' in pattern:
                info['venue'] = m.group(1).strip()
            else:
                info['venue'] = m.group(0).strip()
            break
    
    # イベント名は残ったテキストから推定（短い行）
    lines = text.split('\n')
    short_lines = [l.strip() for l in lines if l.strip() and len(l.strip()) > 2 and len(l.strip()) < 30]
    # 日付や会場名の行を除外
    for line in short_lines:
        if re.search(r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}', line):
            continue
        if re.search(r'\d{4}年\d{1,2}月', line):
            continue
        if info['venue'] and info['venue'] in line:
            continue
        if not info['name'] and not re.search(r'20\d{2}|Sat|Sun|Mon|Tue|Wed|Thu|Fri|1月|2月|3月|4月|5月|6月|7月|8月|9月|10月|11月|12月', line):
            info['name'] = line
            break
    
    return info

def update_gigs_md(info, target_section='upcoming'):
    """抽出した情報を gigs.md に追記"""
    md_path = os.path.join(os.path.dirname(__file__), '..', 'gigs.md')
    
    if not os.path.exists(md_path):
        print(f"gigs.md not found: {md_path}")
        return False
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Table header を見つける
    if target_section == 'upcoming':
        table_pattern = r'(##\s*Upcoming\s*\n\|.*?\n\|[-| :]*\|)\n'
    else:
        table_pattern = r'(##\s*Past\s*\n\|.*?\n\|[-| :]*\|)\n'
    
    m = re.search(table_pattern, content, re.DOTALL)
    if not m:
        print("Table header not found in gigs.md")
        return False
    
    header_end = m.end()
    
    # 新しい行を生成
    new_row = f"| {info['date']} | {info['name']} | {info['venue']} | {info.get('photo', '')} | {info.get('link', '')} |\n"
    
    # 追記
    new_content = content[:header_end] + new_row + content[header_end:]
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    flyers_dir = os.path.join(os.path.dirname(__file__), '..', 'flyers')
    
    if not os.path.exists(flyers_dir):
        print("flyers/ directory not found. Nothing to do.")
        return
    
    jpg_files = glob.glob(os.path.join(flyers_dir, '*.jpg')) + \
                glob.glob(os.path.join(flyers_dir, '*.jpeg')) + \
                glob.glob(os.path.join(flyers_dir, '*.png'))
    
    if not jpg_files:
        print("No flyer images found in flyers/.")
        return
    
    for img_path in sorted(jpg_files):
        filename = os.path.basename(img_path)
        print(f"Processing: {filename}")
        
        text = ocr_image(img_path)
        if not text:
            print(f"  No text detected in {filename}")
            continue
        
        print(f"  OCR text: {text[:200]}...")
        
        info = extract_event_info(text)
        print(f"  Extracted: name={info['name']}, date={info['date']}, venue={info['venue']}")
        
        if info['name'] and info['date']:
            info['photo'] = f"flyers/{filename}"
            update_gigs_md(info, 'upcoming')
            print(f"  Added to gigs.md")
        else:
            print(f"  Could not extract complete event info")

if __name__ == '__main__':
    main()
