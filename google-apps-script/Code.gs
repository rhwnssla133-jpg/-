// Paste into the Apps Script project bound to YOUR new Google spreadsheet.
// All credentials stay in Script Properties, never in the website or this file.
var HEADERS = ['접수 ID', '접수 시각(서울)', '전화번호', '이사 종류', '출발 지역', '도착 지역', '성함 또는 호칭', '희망일', '날짜 미정', '추가 요청사항', '필수 동의', '선택 동의', '국외이전 동의', '동의문 버전', '문의 참조번호', '알림 상태', '알림 시각', '내용 해시'];
var TAB_NAME = '이사 문의';

function onOpen() {
  SpreadsheetApp.getUi().createMenu('OK익스프레스 연동')
    .addItem('1. 초기 설정', 'setup')
    .addItem('2. 내 이메일로 테스트 알림', 'sendTestNotification')
    .addItem('실패·미완료 메일 다시 보내기 (최대 10건)', 'retryFailedNotifications')
    .addToUi();
}

function setup() {
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (!active) throw new Error('새 Google 스프레드시트의 확장 프로그램 > Apps Script에서 실행하세요.');
  var props = PropertiesService.getScriptProperties();
  var email = props.getProperty('ALERT_EMAIL') || Session.getEffectiveUser().getEmail();
  if (!validEmail_(email)) throw new Error('스크립트 속성 ALERT_EMAIL에 수신 이메일 주소를 입력하세요.');
  props.setProperty('SPREADSHEET_ID', active.getId());
  props.setProperty('ALERT_EMAIL', email);
  if (!props.getProperty('WEBHOOK_SECRET')) props.setProperty('WEBHOOK_SECRET', (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, ''));
  if (!props.getProperty('INTEGRATION_ENABLED')) props.setProperty('INTEGRATION_ENABLED', 'false');
  var sheet = active.getSheetByName(TAB_NAME) || active.insertSheet(TAB_NAME);
  if (sheet.getLastRow() === 0) sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  checkHeaders_(sheet);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
  sheet.getRange('C:C').setNumberFormat('@');
  // No customer data, secret, or recipient address in execution logs.
}

function doGet() {
  // Opening the deployment URL never creates a row or sends an email.
  return json_({ ok: true, service: 'OK Express inquiry receiver' });
}

function doPost(e) {
  var lock;
  try {
    var props = PropertiesService.getScriptProperties();
    if (props.getProperty('INTEGRATION_ENABLED') !== 'true') return json_({ ok: false, code: 'DISABLED' });
    if (!e || !e.postData || !e.postData.contents || e.postData.contents.length > 20000) return json_({ ok: false, code: 'INVALID_REQUEST' });
    var envelope = JSON.parse(e.postData.contents);
    var secret = props.getProperty('WEBHOOK_SECRET') || '';
    if (!/^[a-f0-9]{64}$/i.test(secret) || !verifyEnvelope_(envelope, secret, Date.now())) return json_({ ok: false, code: 'UNAUTHORIZED' });
    var item = JSON.parse(envelope.payload);
    validateItem_(item);
    lock = LockService.getScriptLock();
    if (!lock.tryLock(5000)) return json_({ ok: false, code: 'BUSY' });
    var sheet = getSheet_();
    var digest = hex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, envelope.payload, Utilities.Charset.UTF_8));
    var existing = sheet.getLastRow() > 1 ? sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).createTextFinder(item.id).matchEntireCell(true).findNext() : null;
    var row;
    if (existing) {
      row = existing.getRow();
      if (sheet.getRange(row, 18).getDisplayValue() !== digest) return json_({ ok: false, code: 'ID_CONFLICT' });
      if (sheet.getRange(row, 16).getDisplayValue() === 'SENT') return json_({ ok: true, saved: true, emailSent: true, id: item.id, duplicate: true });
    } else {
      row = sheet.getLastRow() + 1;
      var cells = itemToCells_(item).concat(['PENDING', '', digest]).map(safeCell_);
      sheet.getRange(row, 1, 1, HEADERS.length).setNumberFormat('@').setValues([cells]);
      SpreadsheetApp.flush();
    }
    var sent = notifyRow_(sheet, row, props.getProperty('ALERT_EMAIL'));
    return json_({ ok: sent, saved: true, emailSent: sent, id: item.id, code: sent ? 'SAVED_AND_NOTIFIED' : 'EMAIL_FAILED' });
  } catch (_) {
    return json_({ ok: false, code: 'PROCESSING_FAILED' });
  } finally { if (lock && lock.hasLock()) lock.releaseLock(); }
}

function verifyEnvelope_(envelope, secret, now) {
  if (!envelope || envelope.version !== 1 || !Number.isSafeInteger(envelope.timestamp) || Math.abs(now - envelope.timestamp) > 300000 || typeof envelope.nonce !== 'string' || !/^[A-Za-z0-9-]{16,80}$/.test(envelope.nonce) || typeof envelope.payload !== 'string' || envelope.payload.length > 10000 || !/^[a-f0-9]{64}$/.test(envelope.signature || '')) return false;
  var expected = hex_(Utilities.computeHmacSha256Signature(envelope.timestamp + '.' + envelope.nonce + '.' + envelope.payload, secret, Utilities.Charset.UTF_8));
  return equal_(expected, envelope.signature);
}

function equal_(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function hex_(bytes) { return bytes.map(function (b) { return ('0' + ((b + 256) % 256).toString(16)).slice(-2); }).join(''); }
function validEmail_(email) { return typeof email === 'string' && email.length <= 254 && /^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+$/.test(email); }
function safeCell_(value) {
  var string = String(value == null ? '' : value);
  return /^[\s]*[=+\-@]/.test(string) ? "'" + string : string;
}

function validateItem_(item) {
  if (!item || !/^[A-Za-z0-9_-]{8,128}$/.test(item.id || '') || !Number.isFinite(Date.parse(item.createdAt))) throw new Error('Invalid identity');
  if (typeof item.phone !== 'string' || !/^0\d{8,10}$/.test(item.phone) || ['포장이사', '일반이사', '사무실이사'].indexOf(item.moveType) < 0) throw new Error('Invalid fields');
  var limits = { origin: 60, destination: 60, customerName: 30, moveDate: 10, message: 500, consentVersion: 80, reference: 100 };
  Object.keys(limits).forEach(function (key) { if (typeof item[key] !== 'string' || item[key].length > limits[key]) throw new Error('Invalid length'); });
  if (!item.origin.trim() || !item.destination.trim() || !item.consentVersion.trim() || !item.reference.trim() || item.requiredConsent !== 'agreed' || item.overseasConsent !== 'agreed' || ['agreed', 'not-agreed'].indexOf(item.optionalConsent) < 0 || typeof item.dateUndecided !== 'boolean') throw new Error('Missing consent');
  if (item.optionalConsent !== 'agreed' && (item.customerName || item.moveDate || item.message || item.dateUndecided)) throw new Error('Optional data without consent');
}

function checkHeaders_(sheet) {
  if (JSON.stringify(sheet.getRange(1, 1, 1, HEADERS.length).getDisplayValues()[0]) !== JSON.stringify(HEADERS)) throw new Error('시트 열 이름을 변경하지 마세요.');
}

function getSheet_() {
  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('먼저 setup을 실행하세요.');
  var sheet = SpreadsheetApp.openById(id).getSheetByName(TAB_NAME);
  if (!sheet) throw new Error('문의 시트를 찾을 수 없습니다.');
  checkHeaders_(sheet);
  return sheet;
}

function itemToCells_(item) {
  return [item.id, Utilities.formatDate(new Date(item.createdAt), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss'), item.phone, item.moveType, item.origin, item.destination, item.customerName, item.moveDate, item.dateUndecided ? '미정' : '', item.message, item.requiredConsent, item.optionalConsent, item.overseasConsent, item.consentVersion, item.reference];
}

function notifyRow_(sheet, row, email) {
  try {
    if (!validEmail_(email) || MailApp.getRemainingDailyQuota() < 1) throw new Error('Mail unavailable');
    var cells = sheet.getRange(row, 1, 1, 15).getDisplayValues()[0];
    var lines = HEADERS.slice(0, 15).map(function (label, i) { return label + ': ' + (cells[i] || '(미입력)'); });
    var sheetId = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
    MailApp.sendEmail({ to: email, subject: '[OK익스프레스] 새 이사 문의 · ' + cells[0], body: lines.join('\n') + '\n\n문의 시트: https://docs.google.com/spreadsheets/d/' + sheetId + '/edit\n문의 접수는 계약 확정이 아닙니다.' });
    sheet.getRange(row, 16, 1, 2).setValues([['SENT', Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss')]]);
    SpreadsheetApp.flush();
    return true;
  } catch (_) {
    sheet.getRange(row, 16).setValue('FAILED');
    return false;
  }
}

function sendTestNotification() {
  var email = PropertiesService.getScriptProperties().getProperty('ALERT_EMAIL');
  if (!validEmail_(email) || MailApp.getRemainingDailyQuota() < 1) throw new Error('수신 주소·메일 할당량을 확인하세요.');
  MailApp.sendEmail({ to: email, subject: '[OK익스프레스] 연동 테스트', body: 'Google Apps Script의 이메일 전송 테스트입니다. 실제 고객 문의가 아닙니다.\n이 메일 수신만으로 홈페이지 접수부터의 전체 연동이 검증되지는 않습니다.' });
}

function retryFailedNotifications() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) throw new Error('처리 중입니다. 잠시 후 다시 실행하세요.');
  try {
    var sheet = getSheet_();
    var props = PropertiesService.getScriptProperties();
    var statuses = sheet.getLastRow() > 1 ? sheet.getRange(2, 16, sheet.getLastRow() - 1, 1).getDisplayValues() : [];
    var count = 0;
    for (var i = 0; i < statuses.length && count < 10; i++) {
      if (statuses[i][0] !== 'SENT') {
        count++;
        if (!notifyRow_(sheet, i + 2, props.getProperty('ALERT_EMAIL'))) break;
      }
    }
  } finally { lock.releaseLock(); }
}

function json_(value) { return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON); }
