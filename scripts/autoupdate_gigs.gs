/**
 * has — Gig Auto-Update Script
 * 
 * Google Sheets の「拡張機能」→「Apps Script」で貼り付けて使用します。
 * 
 * 機能:
 * 1. Flyer 画像（Google Drive）を OCR で解析
 * 2. イベント情報を自動抽出してシートに追記
 * 3. 日付が過ぎたギグを archive セクションに自動移動
 * 4. 毎日決まった時間に自動実行（トリガー設定）
 */

// ============ 設定 ============
var CONFIG = {
  // シートの設定
  SHEET_NAME: 'Sheet1',       // 使用するシート名
  COLUMN_DATE: 0,             // 日付列 (A=0)
  COLUMN_EVENT: 1,            // イベント名列 (B=1)
  COLUMN_VENUE: 2,            // 会場列 (C=2)
  COLUMN_PHOTO: 3,            // 画像列 (D=3)
  COLUMN_LINK: 4,             // リンク列 (E=4)
  COLUMN_TYPE: -1,            // 型列（自動管理で非使用）
  
  // Drive フォルダ設定
  FLYERS_FOLDER_NAME: 'has-flyers',  // Flyer 画像용 Drive フォルダ名
  
  // OCR 設定
  OCR_MIN_CONFIDENCE: 0.6,      // 最小信頼度閾値
  
  // 自動アーカイブ設定
  ARCHIVE_THRESHOLD_DAYS: 0     // 何日前から archive に移動するか (0=当日)
};

// ============ 起動 ============
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🎵 has Gigs')
    .addItem('Flyer からギグを自動追加', 'runFlyerOCR')
    .addItem('過去ギグを archive に移動', 'archivePastGigs')
    .addItem('全ギグを日付順に整理', 'sortGigsByDate')
    .addSeparator()
    .addItem('トリガー設定...', 'setupTriggers')
    .addToUi();
}

// ============ メイン機能 ============

/**
 * Flyer 画像の OCR を実行してギグ情報を自動抽出・シート追記
 */
function runFlyerOCR() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) {
    sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  }
  
  var folders = DriveApp.getFoldersByName(CONFIG.FLYERS_FOLDER_NAME);
  if (!folders.hasNext()) {
    Logger.log('Drive folder "' + CONFIG.FLYERS_FOLDER_NAME + '" not found.');
    Browser.msgBox('Drive フォルダ "' + CONFIG.FLYERS_FOLDER_NAME + '" が見つかりません。');
    return;
  }
  
  var folder = folders.next();
  var files = folder.getFilesByType(MimeType.JPEG);
  var pngFiles = folder.getFilesByType(MimeType.PNG);
  
  var added = 0;
  
  // JPEG ファイルを処理
  while (files.hasNext()) {
    var file = files.next();
    added += processFlyerImage(file, sheet);
  }
  
  // PNG ファイルを処理
  while (pngFiles.hasNext()) {
    var file = pngFiles.next();
    added += processFlyerImage(file, sheet);
  }
  
  if (added > 0) {
    sortGigsByDate();
    Logger.log(added + '件のギグを追加しました。');
    Browser.msgBox(added + '件のギグを自動追加しました！');
  } else {
    Logger.log('新しいギグ情報は見つかりませんでした。');
    Browser.msgBox('新しいギグ情報は見つかりませんでした。');
  }
}

/**
 * 単一 Flyer 画像を OCR して処理
 */
function processFlyerImage(file, sheet) {
  var fileName = file.getName();
  Logger.log('Processing: ' + fileName);
  
  // 画像を base64 で読み込み
  var blob = file.getBlob();
  var imageBase64 = Utilities.base64Encode(blob.getBytes());
  var mimeType = blob.getContentType();
  
  // Google Cloud Vision API で OCR
  var text = extractTextFromImage(imageBase64, mimeType);
  if (!text || text.length < 10) {
    Logger.log('  OCR text too short or empty');
    return 0;
  }
  
  Logger.log('  OCR text: ' + text.substring(0, 200));
  
  // イベント情報を抽出
  var info = extractEventInfo(text, fileName);
  
  if (!info.name || !info.date) {
    Logger.log('  Could not extract complete event info');
    return 0;
  }
  
  // 重複チェック
  if (isDuplicate(sheet, info.date, info.name)) {
    Logger.log('  Duplicate: ' + info.name + ' on ' + info.date);
    return 0;
  }
  
  // シートに追加
  var lastRow = sheet.getLastRow() + 1;
  sheet.getRange(lastRow, 1).setValue(info.date);
  sheet.getRange(lastRow, 2).setValue(info.name);
  sheet.getRange(lastRow, 3).setValue(info.venue || '');
  sheet.getRange(lastRow, 4).setValue(info.photo || '');
  sheet.getRange(lastRow, 5).setValue(info.link || '');
  
  Logger.log('  Added: ' + info.name + ' | ' + info.venue + ' | ' + info.date);
  return 1;
}

/**
 * Google Cloud Vision API で OCR 実行
 */
function extractTextFromImage(imageBase64, mimeType) {
  var endpoint = 'https://vision.googleapis.com/v1/images:annotate?key=';
  // API キーは スクリプトのプロパティから取得
  var apiKey = PropertiesService.getScriptProperties().getProperty('VISION_API_KEY');
  
  var payload = {
    requests: [{
      image: {
        content: imageBase64
      },
      features: [{
        type: 'TEXT_DETECTION',
        maxResults: 1
      }]
    }]
  };
  
  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  try {
    var response = UrlFetchApp.fetch(endpoint + apiKey, options);
    var json = JSON.parse(response.getContentText());
    
    if (json.responses && json.responses[0] && json.responses[0].textAnnotations) {
      return json.responses[0].textAnnotations[0].description;
    }
  } catch (e) {
    Logger.log('OCR Error: ' + e.toString());
  }
  
  return '';
}

/**
 * OCR 結果からイベント情報を抽出
 */
function extractEventInfo(text, fileName) {
  var info = { name: '', date: '', venue: '', photo: '', link: '' };
  
  // 日付抽出 (YYYY-MM-DD 形式)
  var dateMatch = text.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
  if (dateMatch) {
    var y = parseInt(dateMatch[1]);
    var m = parseInt(dateMatch[2]);
    var d = parseInt(dateMatch[3]);
    info.date = Utilities.formatDate(new Date(y, m-1, d), 'JST', 'yyyy-MM-dd');
  }
  
  // 日本語日付 (2026年7月1日)
  var jpDateMatch = text.match(/(\d{4})年(\d{1,2})月(\d{1,2})日?/);
  if (!info.date && jpDateMatch) {
    var y = parseInt(jpDateMatch[1]);
    var m = parseInt(jpDateMatch[2]);
    var d = parseInt(jpDateMatch[3]);
    info.date = Utilities.formatDate(new Date(y, m-1, d), 'JST', 'yyyy-MM-dd');
  }
  
  // 会場抽出
  var venuePatterns = [
    /(?:会場|LIVE|BAR|CLUB|SQUARE|HALL)\s*[:：]?\s*([^\n,|]+)/i,
    /(?:woda|kitsune|shitamachi|shelter|bulldog|electron|WONDER|COOK)/i,
    /[^、，\s]{2,8}(?:クラブ|ライブ|バー|ホール|スクエア)/
  ];
  
  for (var i = 0; i < venuePatterns.length; i++) {
    var vm = text.match(venuePatterns[i]);
    if (vm) {
      info.venue = vm[1] || vm[0];
      info.venue = info.venue.replace(/\s+/g, ' ').trim();
      break;
    }
  }
  
  // イベント名（画像ファイル名から推測）
  // 例: 20260815_woda.jpg → "woda" を名前に使用
  var nameMatch = fileName.match(/(\d{8})_(.+)/);
  if (nameMatch) {
    info.name = nameMatch[2].replace(/\.[^.]+$/, '');
  }
  
  // 画像URL
  info.photo = file ? file.getUrl() : '';
  
  return info;
}

/**
 * 重複チェック
 */
function isDuplicate(sheet, date, name) {
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    var rowDate = data[i][CONFIG.COLUMN_DATE];
    var rowName = data[i][CONFIG.COLUMN_EVENT];
    
    if (String(rowDate).trim() === date && String(rowName).trim().toLowerCase() === name.toLowerCase()) {
      return true;
    }
  }
  return false;
}

/**
 * 過去ギグを archive セクション（type=past）に自動移動
 */
function archivePastGigs() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  var data = sheet.getDataRange().getValues();
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  
  var archived = 0;
  
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var date = row[CONFIG.COLUMN_DATE];
    
    if (date) {
      var gigDate = new Date(date);
      if (isNaN(gigDate.getTime())) continue;
      
      // 日付が過ぎた場合
      if (gigDate < today) {
        // 既に archive ならスキップ（type列が「past」または「archive」）
        var currentType = String(row[CONFIG.COLUMN_TYPE] || '').toLowerCase();
        if (currentType === 'past' || currentType === 'archive') continue;
        
        sheet.getRange(i + 1, CONFIG.COLUMN_TYPE + 1).setValue('past');
        archived++;
      }
    }
  }
  
  if (archived > 0) {
    Logger.log(archived + '件のギグを archive に移動しました。');
    Browser.msgBox(archived + '件のギグを archive に移動しました！');
  } else {
    Logger.log('移動するギグはありません。');
  }
}

/**
 * 全ギグを日付順に整理
 */
function sortGigsByDate() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  var data = sheet.getDataRange().getValues();
  var header = data[0];
  var rows = data.slice(1);
  
  // 日付でソート（新しい順）
  rows.sort(function(a, b) {
    var da = new Date(a[CONFIG.COLUMN_DATE]);
    var db = new Date(b[CONFIG.COLUMN_DATE]);
    return db - da;
  });
  
  // シートに書き戻す
  sheet.clearContents();
  sheet.getRange(1, 1, 1, header.length).setValues([header]);
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, header.length).setValues(rows);
  }
  
  Logger.log('ギグを日付順に整理しました。');
}

/**
 */
function setupTriggers() {
  // 既存のトリガーを削除
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  
  // 毎日朝6時（JST）に実行
  ScriptApp.newTrigger('archivePastGigs')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .inTimezone('Asia/Tokyo')
    .create();
  
  Logger.log('トリガーを設定しました。毎日朝6時に過去ギグのアーカイブ実行。');
  Browser.msgBox('トリガーを設定しました！');
}
