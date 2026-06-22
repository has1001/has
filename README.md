# has — Official Site

Tokyo-based DJ. House / Disco / Dance Music.

## 🌐 Live

[https://has1001.github.io/has/](https://has1001.github.io/has/)

## 🎵 Gigs Management

Flyer 画像からイベント情報を自動抽出し、サイトに反映する仕組み。

### 使い方（手動 — 即座に反映）

1. **Google シートを開く**
2. 1行目をヘッダーに: `date | event | venue | photo | link`
3. イベント情報を追記:

| date | event | venue | photo | link |
|---|---|---|---|---|
| 2026-07-20 | Midnight House | woda Shibuya | | https://instagram.com/p/xxx |
| 2026-08-15 | Deep Groove | kitsune | https://drive.google.com/... | |

> `type` 列は不要。日付が過ぎたギグは自動で archive に移動します。

### 使い方（自動 — Flyer OCR）

1. Flyer 画像を `flyers/` フォルダに配置
2. `gigs.md` にイベント情報を追記
3. GitHub Actions または Google Apps Script が自動処理

#### 必要な設定

| 設定 | 説明 |
|---|---|
| `GOOGLE_CREDENTIALS` | Google Sheets 用サービスアカウント JSON |
| `GOOGLE_SHEET_ID` | Google Sheets のシート ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Cloud Vision API 用 JSON |

## 📁 File Structure

```
has/
├── index.html          # メインサイト
├── ogp.png             # OGP 画像
├── gigs.md             # Gig 情報管理
├── CHANGES.md          # 改修記録
├── README.md           # このファイル
├── flyers/             # Flyer 画像
├── scripts/            # 自動化スクリプト
│   ├── parse_gigs_md.py
│   ├── sync_to_sheets.py
│   ├── ocr_flyers.py
│   └── autoupdate_gigs.gs
└── .github/
    └── workflows/
        └── sync-gigs.yml
```

## ⚙️ Settings

### Google Sheets

1. シートを作成し、ID をコピー
2. ヘッダーを `date | event | venue | photo | link` に設定
3. `index.html` の `SHEET_ID` を更新（初期値は設定済み）

### GitHub Actions

Secrets に以下の値を設定:

| Secret | 説明 |
|---|---|
| `GOOGLE_CREDENTIALS` | サービスアカウント JSON |
| `GOOGLE_SHEET_ID` | シート ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Vision API JSON |

## 🎨 Contact

- **Email:** [has.dj.has@gmail.com](mailto:has.dj.has@gmail.com)
- **Instagram:** [@hasu](https://instagram.com/hasu/)
- **Twitter:** [@hasu_has](https://twitter.com/hasu_has)
- **SoundCloud:** [hasu_has](https://soundcloud.com/hasu_has)
- **Bandcamp:** [hashas](https://hashas.bandcamp.com/)
- **iF:** [23533](https://iflyer.tv/ja/artist/23533/)
- **RA:** [has](https://www.residentadvisor.net/dj/has)

---

© 2026 has — all rights reserved · tokyo, jp
