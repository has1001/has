# has — 現在地と課題

## ✅ 完了済み

- [x] フライヤー画像からOCRでイベント情報抽出 (Google Cloud Vision API)
- [x] Google Sheets へのデータ自動保存
- [x] Google Sheets ⇄ index.html 自動連携
- [x] 日付ベースの upcoming/archive 自動分類
- [x] PC画面での contact メールアドレスサイズ修正 (64px → 32px)
- [x] GitHub Actions 自動実行 (毎日06:00 JST)
- [x] Google Cloud Billing 有効化

## 🔧 現在地

### 実行中ワークフロー
`GitHub Actions` → 画像OCR → Google Sheets更新 → サイト表示

### 動作する部分
- Google Cloud → OCR 実行 → 日付・イベント名・会場を抽出
- Google Sheets → データ保存
- GitHub → daily workflow 実行
- `index.html` → Google Sheets CSVから読み取り

### 動作しない部分 (不具合)

1. **画像URLがサイトに表示されない**
   - **原因**: スクリプトがシートをクリア→全書き込みするため、ユーザーが手動で入力した画像URLが消える
   - **対応**: 既存データからphoto URLを保存→上書きしないように修正済み

2. **Archivedに自動移動されない**
   - **原因**: シートの`type`列に`past`/`archive`がない
   - **対応**: スクリプトで日付比較後、`past`タグを追加

## 📋 今後の計画

### ステップ1: Google Sheetsへのデータ投入
Google Sheetsに手動でデータを投入:
```
date     | event   | venue  | photo            | link | type
2026-07-17 | Elemog | woda   | Drive画像URL    |      | past
```

### ステップ2: データがサイトに表示されるか確認
1. Google Sheetsにデータが入ったら
2. サイト（`https://has1001.github.io/has/`）をリロード
3. 画像が表示されるか確認

### ステップ3: 自動ワークフロー確認
1. GitHub Actionsで手動実行
2. Sheetが更新されるか確認
3. サイトに反映されるか確認

### 今後の運用
- 新ギグ: Google Sheetsに直接追記
- 画像: Google Driveにアップロード → 共有リンクをphoto列にペースト
- 毎週: ワークフローで過去ギグをarchiveに自動移動
