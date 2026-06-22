# has — Gigs Management

## Gig Flyer から Gig 情報を自動取得する仕組み

### 概要

このリポジトリの `gigs.md` に Flyer 画像のファイルパス（またはURL）と関連情報を追記すると、
GitHub Actions が定期的に実行され、Google Apps Script を経由して Google Sheets の Gig データが自動更新されます。

### 運用フロー

```
1. Flyer画像(this repo) → Google Driveにアップロード
2. gigs.md に Flyer 情報を書式に従って追記
3. GitHub Actions (每晚) が gigs.md を読み取る
4. OCR (Google Cloud Vision API) で画像からイベント名・日付・会場を抽出
5. 既存のデータと比較し、Google Sheets に自動反映
6. Gig サイト (index.html) が Google Sheets から自動取得して表示更新
```

### gigs.md の書式

```markdown
# has — Gigs Management

## Upcoming
| Date (YYYY-MM-DD) | Event Name | Venue | Flyer Image | Link (optional) |
|---|---|---|---|---|
| 2026-08-15 | Midnight House | woda Shibuya | flyers/20260815_woda.jpg | https://instagram.com/p/xxx |
| 2026-09-20 | Deep Groove | kitsune | flyers/20260920_kitsune.jpg | |

## Past
| Date (YYYY-MM-DD) | Event Name | Venue | Flyer Image (optional) | Link (optional) |
|---|---|---|---|---|
| 2026-05-10 | Summer Session | woda Shibuya | flyers/20260510_woda.jpg | https://instagram.com/p/yyy |
```

### 注意点

- **Date** 列は `YYYY-MM-DD` 形式で記入（例: `2026-08-15`）
- **Flyer Image** 列には `flyers/` フォルダ内の画像ファイルパスを記入
- **link** 列は任意（Instagram投稿URLなど）
- Upcoming セクションに追加すると `index.html` の upcoming として表示
- Past セクションに追加すると archive として表示（※ただし `index.html` では日付比較で自動分類されるため、どちらのセクションに書いても正しい位置に表示されます）
- 過去ギグの画像は任意ですが、あるとアーカイブカードの画像として表示されます

### 画像ファイルの配置

Flyer 画像は `flyers/` フォルダに配置してください。

```
has/
├── flyers/
│   └── 20260815_woda.jpg
├── gigs.md
├── index.html
└── ...
```

---

## manual update (GitHub Actions なしの場合)

GitHub Actions と Google Apps Script の連携が設定されていない場合、
または手動で更新する場合は:

1. Google Sheets のシートを開く
2. 1行目にヘッダーを追加: `date | event | venue | photo | link`
3. 2行目以降にイベント情報を追記
4. `index.html` が Google Sheets から自動で読み取り、表示を更新

### Google Sheets へのデータ投入例

| date | event | venue | photo | link |
|---|---|---|---|---|
| 2026-08-15 | Midnight House | woda Shibuya | | https://instagram.com/p/xxx |
| 2026-05-10 | Summer Session | woda Shibuya | https://drive.google.com/... | https://instagram.com/p/yyy |

### 画像のURLについて

Google Drive 画像の場合、共有リンクをそのまま貼り付けると自動的に画像表示用URLに変換されます。
共有設定は「リンクを知っている全員」に設定してください。
