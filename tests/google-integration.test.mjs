import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { createHmac, createHash, randomUUID } from 'node:crypto';
const SECRET = 'ab'.repeat(32); // Synthetic test value only.
function googleMock() {
  const state = { rows: [], props: { SPREADSHEET_ID: 'synthetic-sheet-id', ALERT_EMAIL: 'owner@example.test', FORM_TOKEN_KEY: SECRET, INTEGRATION_ENABLED: 'true', PUBLIC_FORM_CONFIRMED: 'true' }, emails: [], failMail: false, quota: 20, locked: false, standalone: false, createdSheets: 0 };
  const display = value => String(value ?? '').replace(/^'/, '');
  const sheet = {
    getLastRow: () => state.rows.length,
    getRange(row, col, rows = 1, cols = 1) {
      if (typeof row === 'string') return { setNumberFormat() { return this; } };
      return {
        setValues(values) { values.forEach((valuesRow, i) => { state.rows[row + i - 1] ||= []; valuesRow.forEach((v, j) => state.rows[row + i - 1][col + j - 1] = v); }); return this; },
        setValue(v) { return this.setValues([[v]]); }, setNumberFormat() { return this; }, setFontWeight() { return this; },
        getDisplayValues() { return Array.from({ length: rows }, (_, i) => Array.from({ length: cols }, (_, j) => display(state.rows[row + i - 1]?.[col + j - 1]))); },
        getDisplayValue() { return this.getDisplayValues()[0][0]; },
        createTextFinder(value) { return { matchEntireCell() { return this; }, findNext() { const index = state.rows.findIndex((r, i) => i >= row - 1 && i < row - 1 + rows && display(r[col - 1]) === value); return index < 0 ? null : { getRow: () => index + 1 }; } }; },
      };
    },
    setFrozenRows() {},
  };
  const properties = { getProperty: key => state.props[key] ?? null, setProperty(key, value) { state.props[key] = value; return this; } };
  const book = { getId: () => 'synthetic-sheet-id', getSheetByName: () => sheet, insertSheet: () => sheet };
  const signedBytes = buffer => Array.from(buffer, n => n > 127 ? n - 256 : n);
  const context = vm.createContext({
    PropertiesService: { getScriptProperties: () => properties },
    Session: { getEffectiveUser: () => ({ getEmail: () => 'owner@example.test' }), getActiveUser: () => ({ getEmail: () => state.visitor ? '' : 'owner@example.test' }) },
    SpreadsheetApp: { getActiveSpreadsheet: () => state.standalone ? null : book, openById: () => book, create: () => { state.createdSheets++; return book; }, flush() {} },
    Utilities: { Charset: { UTF_8: 'utf8' }, DigestAlgorithm: { SHA_256: 'sha256' }, getUuid: randomUUID,
      computeDigest: (_, value) => signedBytes(createHash('sha256').update(value).digest()),
      computeHmacSha256Signature: (value, key) => signedBytes(createHmac('sha256', key).update(value).digest()),
      formatDate: (date, zone, pattern) => { const value = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date); return pattern === 'yyyy-MM-dd' ? value.slice(0, 10) : value; },
    },
    LockService: { getScriptLock: () => { let held = false; return { tryLock() { if (state.locked) return false; state.locked = true; held = true; return true; }, hasLock: () => held, releaseLock() { state.locked = false; held = false; } }; } },
    MailApp: { getRemainingDailyQuota: () => state.quota, sendEmail(item) { if (state.failMail) throw new Error('Synthetic mail failure'); state.emails.push(item); } },
    HtmlService: { XFrameOptionsMode: { ALLOWALL: 'ALLOWALL' }, createHtmlOutput: html => ({ html, setTitle() { return this; }, addMetaTag() { return this; }, setXFrameOptionsMode() { return this; } }) },
    ContentService: { MimeType: { JSON: 'application/json' }, createTextOutput: content => ({ content, setMimeType() { return this; } }) },
  });
  vm.runInContext(readFileSync(new URL('../google-apps-script/Code.gs', import.meta.url), 'utf8'), context);
  state.rows.push(Array.from(context.HEADERS));
  return { state, context };
}

function inquiry(g, extra = {}, id = '') {
  const config = g.context.getFormConfiguration(id);
  return { id: config.id, sessionToken: config.sessionToken, phone: '010-0000-0000', 'move-type': '포장이사', 'origin-area': '광주 북구 용봉동', 'destination-area': '광주 광산구 수완동', 'required-consent': 'agreed', 'overseas-consent': 'agreed', 'optional-consent': 'not-agreed', 'consent-version': config.policyVersion, ...extra };
}

test('Google direct submission saves a row, emails only the owner, and deduplicates', () => {
  const g = googleMock(), data = inquiry(g);
  const ack = g.context.submitInquiry(data);
  assert.equal(ack.ok, true); assert.equal(ack.saved, true); assert.equal(ack.emailSent, true);
  assert.equal(g.state.rows.length, 2); assert.equal(g.state.rows[1][2], '01000000000');
  assert.equal(g.state.emails.length, 1); assert.equal(g.state.emails[0].to, 'owner@example.test');
  assert.ok(g.state.emails[0].body.includes('01000000000'));
  assert.ok(!g.state.emails[0].subject.includes('01000000000'));
  assert.equal(g.context.submitInquiry(data).duplicate, true);
  assert.equal(g.state.rows.length, 2); assert.equal(g.state.emails.length, 1);
});

test('Setup preserves existing sheet and keeps a new public form disabled', () => {
  const g = googleMock(); g.state.props = {}; g.state.standalone = true;
  g.context.setupAndSendTest();
  assert.equal(g.state.createdSheets, 1); assert.equal(g.state.props.ALERT_EMAIL, 'owner@example.test');
  assert.equal(g.state.props.PUBLIC_FORM_CONFIRMED, 'false');
  assert.equal(g.state.props.INTEGRATION_ENABLED, 'false');
  assert.equal(g.state.emails.length, 1);
  assert.ok(g.state.emails[0].body.includes('synthetic-sheet-id/edit'));
  const key = g.state.props.FORM_TOKEN_KEY;
  assert.match(key, /^[a-f0-9]{64}$/i);
  g.context.setup(); assert.equal(g.state.createdSheets, 1); assert.equal(g.state.props.FORM_TOKEN_KEY, key);
  assert.equal(g.context.getFormConfiguration('').enabled, false);
});

test('Both receiver and public confirmation switches required', () => {
  for (const flag of ['INTEGRATION_ENABLED', 'PUBLIC_FORM_CONFIRMED']) {
    const g = googleMock(), data = inquiry(g); g.state.props[flag] = 'false';
    assert.equal(g.context.getFormConfiguration('').enabled, false);
    assert.equal(g.context.submitInquiry(data).ok, false);
    assert.equal(g.state.rows.length, 1); assert.equal(g.state.emails.length, 0);
  }
});

test('Anonymous customers cannot run setup, test email or administrative retry', () => {
  const g = googleMock(); g.state.visitor = true;
  for (const name of ['setup', 'setupAndSendTest', 'sendTestNotification', 'retryFailedNotifications']) {
    assert.throws(() => g.context[name](), /관리자 Google 계정/);
  }
  assert.equal(g.state.emails.length, 0);
  assert.equal(g.context.submitInquiry(inquiry(g)).saved, true);
});

test('Forged session and missing or outdated consent are rejected', () => {
  for (const changes of [{ sessionToken: '0.fake' }, { 'required-consent': '' }, { 'overseas-consent': '' }, { 'consent-version': 'outdated' }, { 'bot-field': 'spam' }]) {
    const g = googleMock(); assert.equal(g.context.submitInquiry(inquiry(g, changes)).ok, false);
    assert.equal(g.state.rows.length, 1); assert.equal(g.state.emails.length, 0);
  }
});

test('Optional consent excludes data server-side; spreadsheet formulas escaped', () => {
  const g = googleMock();
  assert.equal(g.context.submitInquiry(inquiry(g, { 'customer-name': '=1+1', message: 'not consented' })).saved, true);
  assert.equal(g.state.rows[1][6], ''); assert.equal(g.state.rows[1][9], '');
  assert.equal(g.context.submitInquiry(inquiry(g, { 'optional-consent': 'agreed', 'customer-name': '=1+1', message: '@test', 'date-undecided': 'undecided' })).saved, true);
  assert.equal(g.state.rows[2][6], "'=1+1"); assert.equal(g.state.rows[2][9], "'@test"); assert.equal(g.state.rows[2][8], '미정');
});

test('Email failure retains receipt; manual retry restores notification', () => {
  const g = googleMock(); g.state.quota = 0; const data = inquiry(g);
  const ack = g.context.submitInquiry(data);
  assert.equal(ack.saved, true); assert.equal(ack.emailSent, false); assert.equal(g.state.rows[1][15], 'FAILED');
  g.state.quota = 10; g.context.retryFailedNotifications();
  assert.equal(g.state.rows[1][15], 'SENT'); assert.equal(g.state.emails.length, 1);
  g.context.submitInquiry(data); assert.equal(g.state.emails.length, 1);
});

test('Phone, detailed address, excessive length and past dates validated', () => {
  for (const changes of [{ phone: '123' }, { 'origin-area': '광주 북구 101동 202호' }, { 'destination-area': 'x'.repeat(61) }, { 'optional-consent': 'agreed', message: 'x'.repeat(501) }, { 'optional-consent': 'agreed', 'move-date': '2020-01-01' }]) {
    const g = googleMock(); assert.equal(g.context.submitInquiry(inquiry(g, changes)).ok, false); assert.equal(g.state.rows.length, 1);
  }
});

test('Daily limit bounds new submissions; retries do not consume it', () => {
  const g = googleMock(); g.state.props.MAX_DAILY_INQUIRIES = '1'; const data = inquiry(g);
  assert.equal(g.context.submitInquiry(data).saved, true);
  assert.equal(g.context.submitInquiry(inquiry(g)).code, 'DAILY_LIMIT');
  assert.equal(g.context.submitInquiry(data).duplicate, true);
  assert.equal(g.state.rows.length, 2); assert.equal(g.state.props.COUNT_VALUE, '1');
});

test('Modified content cannot overwrite a receipt, raw HTTP POST cannot bypass form', () => {
  const g = googleMock(), data = inquiry(g);
  g.context.submitInquiry(data);
  assert.equal(g.context.submitInquiry({ ...data, 'origin-area': '광주 남구 봉선동' }).code, 'REFERENCE_CONFLICT');
  assert.equal(JSON.parse(g.context.doPost().content).ok, false); assert.equal(g.state.rows.length, 2);
});

test('Embedded Google form renders without credentials and status exposes only flags', () => {
  const g = googleMock(), channel = randomUUID();
  const html = g.context.doGet({ parameter: { channel } }).html;
  const boot = JSON.parse(html.match(/<script id="form-bootstrap"[^>]*>(.*?)<\/script>/s)[1]);
  assert.equal(boot.channel, channel); assert.ok(html.includes('google.script.run'));
  assert.ok(!html.includes(SECRET)); assert.ok(!html.includes('owner@example.test'));
  const status = JSON.parse(g.context.doGet({ parameter: { status: '1' } }).content);
  assert.equal(status.mode, 'direct-google-form'); assert.equal(status.enabled, true);
  assert.ok(!Object.values(status).includes('synthetic-sheet-id'));
});
