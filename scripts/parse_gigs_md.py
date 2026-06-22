#!/usr/bin/env python3
"""
gigs.md から upcoming と past のギグ情報をパースする。
結果は JSON として stdout に出力。
"""
import json
import re
import sys
import os

def parse_gigs_md(filepath):
    """gigs.md をパースしてギグ情報をリストとして返す"""
    if not os.path.exists(filepath):
        print("gigs.md not found, skipping.", file=sys.stderr)
        return {'upcoming': [], 'past': []}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    upcoming = []
    past = []

    # セクションを抽出
    upcoming_match = re.search(r'##\s*Upcoming\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    past_match = re.search(r'##\s*Past\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)

    def parse_table_block(text):
        """Markdown テーブルをパースしてリストのリストとして返す"""
        lines = text.strip().split('\n')
        rows = []
        for line in lines:
            line = line.strip()
            if line.startswith('|') and not any(c in line for c in ['-|', '--']):
                cells = [c.strip() for c in line.split('|')]
                cells = [c for c in cells if c]  # 空要素を除外
                if len(cells) >= 3:
                    rows.append(cells)
        return rows

    if upcoming_match:
        rows = parse_table_block(upcoming_match.group(1))
        for row in rows:
            if len(row) >= 3:
                item = {
                    'date': row[0],
                    'name': row[1],
                    'venue': row[2],
                    'photo': row[3] if len(row) > 3 else '',
                    'link': row[4] if len(row) > 4 else ''
                }
                if item['date'] and item['name']:
                    upcoming.append(item)

    if past_match:
        rows = parse_table_block(past_match.group(1))
        for row in rows:
            if len(row) >= 3:
                item = {
                    'date': row[0],
                    'name': row[1],
                    'venue': row[2],
                    'photo': row[3] if len(row) > 3 else '',
                    'link': row[4] if len(row) > 4 else ''
                }
                if item['date'] and item['name']:
                    past.append(item)

    # date でソート（新しい順）
    upcoming.sort(key=lambda x: x['date'], reverse=True)
    past.sort(key=lambda x: x['date'], reverse=True)

    return {'upcoming': upcoming, 'past': past}

if __name__ == '__main__':
    filepath = os.path.join(os.path.dirname(__file__), '..', 'gigs.md')
    result = parse_gigs_md(filepath)
    print(json.dumps(result, ensure_ascii=False))
