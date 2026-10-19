import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { createHmac, createHash, randomUUID } from 'node:crypto';
import { envelope, integrationReady, makeHandler, normalizeSubmission } from '../netlify/functions/submission-created.mjs';
import baseConfig from '../config.json' with { type: 'json' };

const SECRET = 'ab'.repeat(32); // Synthetic test secret. Never used for deployment.
const SCRIPT_URL = 'https://script.google.com/macros/s/synthetic-test-deployment/exec';
const env = { GOOGLE_SHEETS_ENABLED: 'true', GOOGLE_APPS_SCRIPT_URL: SCRIPT_URL, GOOGLE_WEBHOOK_SECRET: SECRET };
function configured() {
  const c = structuredClone(baseConfig), g = c.integrations.googleSheets;
  Object.assign(g, { requested: true, deliveryConfigured: true, privacyReviewedOn: '2026-10-19' });
  for (const [key, value] of Object.entries(g.transfer)) g.transfer[key] = Array.isArray(value) ? ['테스트 전용 값'] : '테스트 전용 값';
  return c;
}
function fixture(overrides = {}) {
  return { id: 'submission_test_0001', form_name: 'ok-express-inquiry', created_at: '2026-10-19T01:00:00Z', data: {
    'form-name': 'ok-express-inquiry', phone: '010-0000-0000', 'move-type': '포장이사', 'origin-area': '광주 북구 용봉동', 'destination-area': '광주 광산구 수완동',
    'required-consent': 'agreed', 'overseas-consent': 'agreed', 'optional-consent': 'not-agreed', 'consent-version': baseConfig.site.policyVersion, 'inquiry-reference': 'OK-synthetic-test', ...overrides,
  } };
}
const event = payload => ({ body: JSON.stringify({ payload }) });

function googleMock() {
  const state = { rows: [], props: { SPREADSHEET_ID: 'synthetic-sheet-id', ALERT_EMAIL: 'owner@example.test', WEBHOOK_SECRET: SECRET, INTEGRATION_ENABLED: 'true' }, emails: [], failMail: false, quota: 20, locked: false };
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
    Session: { getEffectiveUser: () => ({ getEmail: () => 'owner@example.test' }) },
    SpreadsheetApp: { getActiveSpreadsheet: () => book, openById: () => book, flush() {} },
    Utilities: { Charset: { UTF_8: 'utf8' }, DigestAlgorithm: { SHA_256: 'sha256' }, getUuid: randomUUID,
      computeDigest: (_, value) => signedBytes(createHash('sha256').update(value).digest()),
      computeHmacSha256Signature: (value, key) => signedBytes(createHmac('sha256', key).update(value).digest()),
      formatDate: date => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date),
    },
    LockService: { getScriptLock: () => { let held = false; return { tryLock() { if (state.locked) return false; state.locked = true; held = true; return true; }, hasLock: () => held, releaseLock() { state.locked = false; held = false; } }; } },
    MailApp: { getRemainingDailyQuota: () => state.quota, sendEmail(item) { if (state.failMail) throw new Error('Synthetic mail failure'); state.emails.push(item); } },
    ContentService: { MimeType: { JSON: 'application/json' }, createTextOutput: content => ({ content, setMimeType() { return this; } }) },
  });
  vm.runInContext(readFileSync(new URL('../google-apps-script/Code.gs', import.meta.url), 'utf8'), context);
  state.rows.push(Array.from(context.HEADERS));
  const post = body => JSON.parse(context.doPost({ postData: { contents: JSON.stringify(body) } }).content);
  const fetchImpl = async (_, options) => ({ ok: true, url: 'https://script.googleusercontent.com/synthetic-response', json: async () => post(JSON.parse(options.body)) });
  return { state, context, post, fetchImpl };
}

test('Default and incomplete settings never forward customer data', async () => {
  let calls = 0;
  const handler = makeHandler({ env, siteConfig: baseConfig, fetchImpl: () => { calls++; } });
  assert.equal((await handler(event(fixture()))).statusCode, 200);
  assert.equal(calls, 0);
  const c = configured(); c.integrations.googleSheets.transfer.countries = [];
  assert.equal(integrationReady(c), false);
});

test('Netlify event -> signed Apps Script -> sheet and email; duplicates deduplicated', async () => {
  const g = googleMock();
  const handler = makeHandler({ env, siteConfig: configured(), fetchImpl: g.fetchImpl });
  const input = event(fixture({ message: 'must be omitted', 'customer-name': 'not consented' }));
  assert.equal((await handler(input)).statusCode, 200);
  assert.equal(g.state.rows.length, 2);
  assert.equal(g.state.rows[1][2], '01000000000');
  assert.equal(g.state.rows[1][6], '');
  assert.equal(g.state.rows[1][9], '');
  assert.equal(g.state.rows[1][15], 'SENT');
  assert.equal(g.state.emails.length, 1);
  assert.equal(g.state.emails[0].to, 'owner@example.test');
  assert.ok(!g.state.emails[0].subject.includes('01000000000'));
  assert.ok(g.state.emails[0].body.includes('01000000000'));
  assert.equal((await handler(input)).statusCode, 200);
  assert.equal(g.state.rows.length, 2);
  assert.equal(g.state.emails.length, 1);
});

test('Tampered signatures and expired envelopes cannot write rows or send mail', () => {
  const g = googleMock(), item = normalizeSubmission(fixture());
  const bad = envelope(item, SECRET); bad.payload += ' ';
  assert.equal(g.post(bad).ok, false);
  assert.equal(g.post(envelope(item, SECRET, Date.now() - 360000)).ok, false);
  assert.equal(g.state.rows.length, 1);
  assert.equal(g.state.emails.length, 0);
});

test('Sheet formulas escaped and optional fields carried only with consent', async () => {
  const g = googleMock();
  const handler = makeHandler({ env, siteConfig: configured(), fetchImpl: g.fetchImpl });
  assert.equal((await handler(event(fixture({ 'optional-consent': 'agreed', 'customer-name': '=1+1', message: ' @test', 'date-undecided': 'undecided' })))).statusCode, 200);
  assert.equal(g.state.rows[1][6], "'=1+1");
  assert.equal(g.state.rows[1][9], "'@test");
  assert.equal(g.state.rows[1][8], '미정');
});

test('Mail failure preserves row; manual retry sends and later event avoids duplicate', async () => {
  const g = googleMock(); g.state.quota = 0;
  const handler = makeHandler({ env, siteConfig: configured(), fetchImpl: g.fetchImpl });
  assert.equal((await handler(event(fixture()))).statusCode, 502);
  assert.equal(g.state.rows.length, 2);
  assert.equal(g.state.rows[1][15], 'FAILED');
  assert.equal(g.state.emails.length, 0);
  g.state.quota = 10;
  g.context.retryFailedNotifications();
  assert.equal(g.state.rows[1][15], 'SENT');
  assert.equal(g.state.emails.length, 1);
  assert.equal((await handler(event(fixture()))).statusCode, 200);
  assert.equal(g.state.emails.length, 1);
});

test('Network errors and unconfirmed Google acknowledgments return failure', async () => {
  for (const fetchImpl of [async () => { throw new Error('Offline'); }, async () => ({ ok: true, url: SCRIPT_URL, json: async () => ({ ok: true, saved: true, emailSent: false }) })]) {
    const handler = makeHandler({ env, siteConfig: configured(), fetchImpl });
    assert.equal((await handler(event(fixture()))).statusCode, 502);
  }
});

test('Other forms, missing consent, invalid endpoint, and conflicting IDs rejected', async () => {
  const g = googleMock();
  const handler = makeHandler({ env, siteConfig: configured(), fetchImpl: g.fetchImpl });
  const other = fixture(); other.form_name = 'other'; other.data['form-name'] = 'other';
  assert.equal((await handler(event(other))).statusCode, 200);
  assert.equal((await handler(event(fixture({ 'overseas-consent': '' })))).statusCode, 400);
  const wrong = makeHandler({ env: { ...env, GOOGLE_APPS_SCRIPT_URL: 'https://example.test/exec' }, siteConfig: configured(), fetchImpl: g.fetchImpl });
  assert.equal((await wrong(event(fixture()))).statusCode, 503);
  assert.equal((await handler(event(fixture()))).statusCode, 200);
  assert.equal((await handler(event(fixture({ 'origin-area': '광주 남구 봉선동' })))).statusCode, 502);
  assert.equal(g.state.rows.length, 2);
});

test('Setup uses current Google account, preserves settings and keeps receiver disabled', () => {
  const g = googleMock();
  g.state.props = {}; // Properties adapter reads current object.
  g.context.setup();
  assert.equal(g.state.props.ALERT_EMAIL, 'owner@example.test');
  assert.equal(g.state.props.INTEGRATION_ENABLED, 'false');
  assert.match(g.state.props.WEBHOOK_SECRET, /^[a-f0-9]{64}$/i);
  const secret = g.state.props.WEBHOOK_SECRET;
  g.context.setup();
  assert.equal(g.state.props.WEBHOOK_SECRET, secret);
  assert.equal(g.state.emails.length, 0);
});
