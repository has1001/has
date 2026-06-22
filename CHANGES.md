# 改修記録 (2026-06-23)

## 1. フライヤー画像から gigs 情報を自動アップデートする仕組み

### 概要
Flyer 画像を OCR で解析し、イベント名・日付・会場を自動抽出して Google Sheets に反映する仕組みを作成しました。

### ファイル構成
```
has/
├── gigs.md                          # Gig 情報管理ファイル（書式定义）
├── .github/workflows/sync-gigs.yml  # GitHub Actions ワークフロー
└── scripts/
    ├── parse_gigs_md.py             # gigs.md パサー
    ├── sync_to_sheets.py            # Google Sheets 同期スクリプト
    ├── ocr_flyers.py                # Flyer OCR スクリプト
    └── autoupdate_gigs.gs           # Google Apps Script (Sheet で実行)
```

### 運用方法（2つのパターン）

**パターンA: GitHub Actions + OCR（自動）**
1. Flyer 画像を `flyers/` フォルダに配置
2. `gigs.md` にイベント情報を追記
3. GitHub Actions が自動で OCR 実行 → Google Sheets に反映

**パターンB: Google Sheets で直接入力（手動）**
1. Google シートの 1行目をヘッダーに: `date | event | venue | photo | link`
2. 2行目以降にイベント情報を追記
3. `index.html` が自動で Google Sheets から読み取り表示更新

### Google Sheets のヘッダー（新フォーマット）
| 列 | 項目 | 書式 |
|---|---|---|
| A | date | `YYYY-MM-DD` または `2026年7月1日` |
| B | event | イベント名 |
| C | venue | 会場名 |
| D | photo | 画像URL（Drive共有リンク可） |
| E | link | リンク（任意） |

> **注意**: `type` 列は削除。日付に基づき自動で upcoming/past を分類します。

---

## 2. 日付が過ぎた gig を archive セクションに自動移行

### 変更内容
`index.html` の JavaScript を修正:

**Before:** シートの `type` 列（upcoming / past）で分類
**After:** 現在日付とイベント日付を比較して自動分類

- 日付が **今日以降** → `upcoming` セクションに表示
- 日付が **昨日まで** → `archive` セクションに自動移動

### 動作
```javascript
var today = new Date(); today.setHours(0,0,0,0);
if (item.date && item.date < today) {
  past.push(item);    // archive へ
} else {
  upcoming.push(item); // upcoming へ
}
```

### Google Apps Script での定期自動移行（任意）
`scripts/autoupdate_gigs.gs` の `archivePastGigs()` 関数を
Google Sheets の「拡張機能」→「Apps Script」→「トリガー」で
毎日朝6時に実行するように設定できます。

---

## 3. PCで contact の連絡先サイズを修正

### 変更前
```css
.contact-mail {
  font-size: clamp(24px, 5.6vw, 64px);
}
/* PCで最大 64px → 大きすぎる */
```

### 変更後
```css
.contact-mail {
  font-size: clamp(16px, 2.2vw, 32px);
}
/* PCで最大 32px → 適切なサイズ */
```

| 画面 | 変更前 | 変更後 |
|---|---|---|
| 最小 | 24px | 16px |
| 流体 | 5.6vw | 2.2vw |
| 最大(PC) | **64px** | **32px** |

---

## 設定が必要な項目

### Google Sheets
1. シートのURLとIDを `.env` に設定
2. ヘッダーを `date | event | venue | photo | link` に変更

### Google Cloud Vision API（OCR用）
1. Google Cloud Console で Vision API を有効化
2. サービスアカウント作成 → キーJSONをダウンロード
3. GitHub Secrets に `GOOGLE_APPLICATION_CREDENTIALS` として登録

### Google Apps Script（自動アーカイブ用）
1. Google Sheets で「拡張機能」→「Apps Script」を選択
2. `scripts/autoupdate_gigs.gs` の内容を貼り付け
3. スクリプトプロパティに `VISION_API_KEY` を設定
4. トリガーを「毎日朝6時」に設定
