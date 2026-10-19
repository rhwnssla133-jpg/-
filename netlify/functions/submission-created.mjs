// Netlify's reserved form-submission event. No customer-facing endpoint is added.
import { createHmac, randomUUID } from 'node:crypto';
import config from '../../config.json' with { type: 'json' };

export const FORM_NAME = 'ok-express-inquiry';
export const response = (statusCode, code) => ({
  statusCode, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  body: JSON.stringify({ code }),
});

function text(value, max, required = false) {
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) throw new Error('Invalid field');
  return value.trim();
}

export function normalizeSubmission(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('Invalid payload');
  const data = payload.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid data');
  const name = payload.form_name || data['form-name'];
  if (name !== FORM_NAME || (payload.form_name && data['form-name'] && payload.form_name !== data['form-name'])) return null;
  if (payload.spam === true || data['bot-field']) return null;
  const id = text(payload.id, 128, true);
  if (!/^[A-Za-z0-9_-]{8,128}$/.test(id)) throw new Error('Invalid submission ID');
  const createdAt = text(payload.created_at, 50, true);
  if (!Number.isFinite(Date.parse(createdAt))) throw new Error('Invalid timestamp');
  if (data['required-consent'] !== 'agreed' || data['overseas-consent'] !== 'agreed') throw new Error('Missing consent');
  const phone = text(data.phone, 20, true).replace(/[\s()-]/g, '').replace(/^\+82/, '0');
  if (!/^(?:010\d{8}|01[16789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8}|050\d{8,9})$/.test(phone)) throw new Error('Invalid phone');
  const moveType = text(data['move-type'], 10, true);
  if (!['포장이사', '일반이사', '사무실이사'].includes(moveType)) throw new Error('Invalid type');
  const optional = data['optional-consent'] === 'agreed';
  const undecided = optional && data['date-undecided'] === 'undecided';
  const date = optional && !undecided ? text(data['move-date'] || '', 10) : '';
  if (date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date + 'T00:00:00Z')) || new Date(date + 'T00:00:00Z').toISOString().slice(0, 10) !== date)) throw new Error('Invalid date');
  const origin = text(data['origin-area'], 60, true), destination = text(data['destination-area'], 60, true);
  if ([origin, destination].some(area => /(?:\d+\s*(?:호|번지)|(?:^|\s)\d{2,4}동(?:\s|$)|\d{1,4}-\d{1,4}|(?:로|길)\s*\d+|비밀번호|공동현관)/.test(area))) throw new Error('Detailed address');
  return {
    id, createdAt, phone, moveType, origin, destination,
    customerName: optional ? text(data['customer-name'] || '', 30) : '',
    moveDate: date, dateUndecided: undecided,
    message: optional ? text(data.message || '', 500) : '',
    requiredConsent: 'agreed', optionalConsent: optional ? 'agreed' : 'not-agreed',
    overseasConsent: 'agreed', consentVersion: text(data['consent-version'], 80, true),
    reference: text(data['inquiry-reference'] || id, 100, true),
  };
}

export function envelope(submission, secret, now = Date.now(), nonce = randomUUID()) {
  const payload = JSON.stringify(submission);
  return { version: 1, timestamp: now, nonce, payload,
    signature: createHmac('sha256', secret).update(`${now}.${nonce}.${payload}`).digest('hex') };
}

export function integrationReady(c) {
  const g = c.integrations?.googleSheets;
  const t = g?.transfer;
  const has = value => typeof value === 'string' && !!value.trim() && !['확인 필요', '확인 중', '미정'].includes(value.trim());
  return g?.requested === true && g.deliveryConfigured === true && has(g.privacyReviewedOn) &&
    ['recipientLegalName', 'recipientContact', 'items', 'time', 'method', 'purpose', 'retention', 'dpaUrl', 'verifiedOn'].every(key => has(t?.[key])) &&
    ['countries', 'subprocessors'].every(key => Array.isArray(t?.[key]) && t[key].length > 0 && t[key].every(has));
}

export function makeHandler({ env = process.env, fetchImpl = fetch, siteConfig = config } = {}) {
  return async (event) => {
    // Receiving customer data in Google is opt-in, with privacy requirements checked.
    if (env.GOOGLE_SHEETS_ENABLED !== 'true' || !integrationReady(siteConfig)) return response(200, 'GOOGLE_INTEGRATION_DISABLED');
    let submission;
    try {
      if (typeof event.body !== 'string' || Buffer.byteLength(event.body) > 65536) throw new Error('Invalid event');
      submission = normalizeSubmission(JSON.parse(event.body).payload);
      if (!submission) return response(200, 'IGNORED_FORM');
    } catch { return response(400, 'INVALID_SUBMISSION'); }
    let url;
    try {
      // Deployment URL is public configuration; the signing key is server-only.
      url = new URL(env.GOOGLE_APPS_SCRIPT_URL || siteConfig.integrations?.googleSheets?.webAppUrl);
      if (url.protocol !== 'https:' || url.hostname !== 'script.google.com' || !/^\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(url.pathname) || url.search || url.hash || url.username || url.password || url.port) throw new Error('Invalid URL');
      if (!/^[a-f0-9]{64}$/i.test(env.GOOGLE_WEBHOOK_SECRET || '')) throw new Error('Invalid secret');
    } catch { return response(503, 'GOOGLE_CONFIGURATION_REQUIRED'); }
    try {
      const result = await fetchImpl(url.href, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(envelope(submission, env.GOOGLE_WEBHOOK_SECRET)),
        signal: AbortSignal.timeout(20000), redirect: 'follow',
      });
      if (!result.ok) throw new Error('Failed request');
      if (result.url && !['script.google.com', 'script.googleusercontent.com'].includes(new URL(result.url).hostname)) throw new Error('Unexpected redirect');
      const ack = await result.json();
      if (ack.ok !== true || ack.saved !== true || ack.emailSent !== true || ack.id !== submission.id) throw new Error('Not confirmed');
      return response(200, 'GOOGLE_SAVED_AND_NOTIFIED');
    } catch {
      // Never log payload, email, script URL, secret, or provider response body.
      return response(502, 'GOOGLE_DELIVERY_NOT_CONFIRMED');
    }
  };
}

export const handler = makeHandler();
