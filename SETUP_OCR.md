# Flyer OCR 自動連携セットアップ手順

## 1. Google Cloud API キーの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 右上でプロジェクトを選択（作成済みでなければ新規作成）
3. **「APIとサービス」** → **「ライブラリ」**
4. **「Cloud Vision API」** を検索 → **「有効にする」**

### API キーの作成
1. **「APIとサービス」** → **「認証情報」**
2. **「認証情報を作成」** → **「APIキー」**
3. 表示されたキーをコピーして控える
4. （オプション）キーの制限を設定（IP / HTTP リファラー）

---

## 2. Google Sheets の準備

1. [Google Sheets](https://sheets.google.com/) で新規シートを作成
2. シートのURLから **シートID** をコピー

例:
```
https://docs.google.com/spreadsheets/d/xxxxxxxxxxxxxxxxxxxxxxxxxxx/edit
                        ↑ ここがシートID
```

3. 1行目にヘッダーを手動で入力:

| A | B | C | D | E |
|---|---|---|---|---|
| date | event | venue | photo | link |

---

## 3. サービスアカウントの作成（GSuite 用）

1. **「APIとサービス」** → **「認証情報」**
2. **「認証情報を作成」** → **「サービスアカウント」**
3. 名前を入力 → **「作成」** → **「飛ばす」**
4. 作成したサービスアカウントをクリック → **「キー」** タブ
5. **「新しいキーを追加」** → **「JSON」** で作成
6. 以下の JSON ファイルがダウンロードされる

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "..."
}
```

7. この JSON の中身を全体コピーして後で使用

---

## 4. Drive フォルダの共有

1. Google Drive でフォルダを作成 → **`has-flyers`** にする
2. Flyer 画像をアップロード
3. 右上の「共有設定」→ **「リンクを知っている全員」** に設定
4. 右上の共有アイコン → **「リンクをコピー」**
5. URLから **フォルダID** をコピー

例:
```
https://drive.google.com/drive/folders/xxxxxxxxxxxxxxxxxxxxxxxxxxx
                                                        ↑ ここがフォルダID
```

---

## 5. GitHub Secrets の設定

1. GitHub リポジトリページを開く
2. **「Settings」** → **「Secrets and variables」** → **「Actions」**
3. **「New repository secret」** をクリック

| シークレット名 | 値 |
|---|---|
| `GOOGLE_CREDENTIALS` | 手順3でダウンロードしたJSON の全文 |
| `GOOGLE_SHEET_ID` | 手順2でコピーしたシートID |
| `DRIVE_FOLDER_ID` | 手順4でコピーしたフォルダID |

> **注意点:**
> - JSON は改行を含むので、`"` の前にスペースが入らないよう注意
> - シートIDは `https://docs.google.com/spreadsheets/d/` と `/edit` の間の文字列のみ

---

## 6. 動作確認

GitHub Actions のページから手動実行:

1. **「Actions」** タブ
2. **「Flyer OCR → Google Sheets」** ワークフロー
3. **「Run workflow」** → **「Run」**

✓ 正常に実行されると、Google Sheets にイベント情報が追記されます。

---

## フローまとめ

```
flyers/
└── 20260717_elemog.jpeg    ← Flyer 画像をここに置く

GitHub Actions (毎日 06:00 JST)
  ↓ Google Cloud Vision API で OCR
  ↓ イベント情報を抽出
  ↓ Google Sheets に追記
  ↓
index.html がシートから自動取得 → サイトに反映
```
