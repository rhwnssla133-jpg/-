// Runs only inside Google Apps Script HtmlService. No fetch/no-cors substitute.
const boot = JSON.parse(document.getElementById('form-bootstrap').textContent);
const form = document.getElementById('inquiry-form');
const fields = document.getElementById('inquiry-fields');
const submit = document.getElementById('submit-inquiry');
const status = document.getElementById('form-status');
const summary = document.getElementById('error-summary');
const consent = document.getElementById('optional-consent');
const dialog = document.getElementById('success-dialog');
const optionalNames = ['customer-name', 'move-date', 'date-undecided', 'message'];
const get = name => form.elements.namedItem(name);
let reference = '', enabled = false, pending = false, attempt = 0;
const tellParent = (type, extra = {}) => {
  if (window.top !== window) window.top.postMessage({ type, channel: boot.channel, ...extra }, boot.origin);
};
const resize = () => tellParent('ok-express-form-height', { height: document.body.scrollHeight });
new ResizeObserver(resize).observe(document.body);
document.addEventListener('focusin', () => tellParent('ok-express-form-focus', { active: !!document.activeElement?.closest('form') }));
document.addEventListener('focusout', () => setTimeout(() => tellParent('ok-express-form-focus', { active: !!document.activeElement?.closest('form') }), 0));
function rpc(method, data) {
  return new Promise((resolve, reject) => google.script.run.withSuccessHandler(resolve).withFailureHandler(() => reject(new Error('Google request failed')))[method](data));
}
function clearErrors(names) {
  names.forEach(name => { get(name)?.removeAttribute('aria-invalid'); const message = document.getElementById(`${name}-error`); if (message) message.textContent = ''; });
}
function updateOptional() {
  optionalNames.forEach(name => {
    const input = get(name); input.disabled = !enabled || !consent.checked;
    if (!consent.checked) { if (input.type === 'checkbox') input.checked = false; else input.value = ''; }
  });
  if (consent.checked && get('date-undecided').checked) { get('move-date').value = ''; get('move-date').disabled = true; }
  clearErrors(optionalNames); resize();
}
function errorsShown(errors) {
  summary.replaceChildren(); const title = document.createElement('strong'); title.textContent = '입력한 내용을 확인해 주세요.';
  const ul = document.createElement('ul');
  Object.entries(errors).forEach(([name, message]) => {
    get(name).setAttribute('aria-invalid', 'true'); document.getElementById(`${name}-error`).textContent = message;
    const li = document.createElement('li'), a = document.createElement('a'); a.href = `#${name}`; a.textContent = message;
    a.addEventListener('click', e => { e.preventDefault(); get(name).focus(); }); li.append(a); ul.append(li);
  });
  summary.append(title, ul); summary.focus(); resize();
}
function failure(message) {
  status.replaceChildren(document.createTextNode(message + ' '));
  const a = document.createElement('a'); a.href = boot.phoneLink; a.textContent = '전화 문의'; status.append(a); resize();
}
consent.addEventListener('change', updateOptional);
get('date-undecided').addEventListener('change', updateOptional);
get('move-date').min = seoulDate();
document.getElementById('close-success').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => submit.focus({ preventScroll: true }));
async function init() {
  try {
    const config = await rpc('getFormConfiguration', '');
    enabled = config.enabled === true; reference = config.id || '';
    fields.disabled = !enabled; get('consent-version').value = config.policyVersion;
    const availability = document.getElementById('availability-notice');
    availability.hidden = enabled;
    availability.textContent = enabled ? '' : '온라인 문의를 준비하고 있습니다. 지금은 전화로 문의해 주세요.';
    submit.textContent = enabled ? '이사 문의 접수하기 ↗' : '현재 전화 문의만 가능합니다';
    updateOptional(); tellParent('ok-express-form-ready'); resize();
  } catch { failure('문의창을 준비하지 못했습니다. 다시 열거나 전화로 문의해 주세요.'); tellParent('ok-express-form-ready'); }
}
form.addEventListener('submit', async event => {
  event.preventDefault(); if (!enabled || pending) return;
  summary.replaceChildren(); status.textContent = '';
  clearErrors(['phone', 'move-type', 'origin-area', 'destination-area', 'customer-name', 'move-date', 'message', 'required-consent', 'overseas-consent']);
  const values = Object.fromEntries(new FormData(form).entries());
  const errors = validateInquiry(values);
  if (Object.keys(errors).length) { errorsShown(errors); return; }
  const payload = {};
  for (const key of ['phone', 'move-type', 'origin-area', 'destination-area', 'required-consent', 'overseas-consent', 'consent-version', 'bot-field']) payload[key] = values[key] || '';
  payload['optional-consent'] = consent.checked ? 'agreed' : 'not-agreed';
  if (consent.checked) optionalNames.forEach(key => { if (values[key]) payload[key] = values[key]; });
  pending = true; fields.disabled = true; submit.disabled = true; form.setAttribute('aria-busy', 'true');
  submit.textContent = '문의 내용을 보내고 있습니다…'; status.textContent = '접수 응답을 기다리고 있습니다.';
  const current = ++attempt;
  const timer = setTimeout(() => {
    if (current !== attempt) return;
    attempt++; pending = false; fields.disabled = false; submit.disabled = false; form.removeAttribute('aria-busy');
    submit.textContent = '다시 접수 확인하기 ↗';
    failure('접수 완료를 확인하지 못했습니다. 입력은 유지됩니다. 이미 접수되었을 수도 있으니 전화로 확인하거나 다시 시도해 주세요.');
  }, 30000);
  try {
    const session = await rpc('getFormConfiguration', reference);
    if (current !== attempt) return;
    if (!session.enabled) throw new Error('Reception disabled');
    reference = session.id; payload.id = reference; payload.sessionToken = session.sessionToken;
    const ack = await rpc('submitInquiry', payload);
    if (current !== attempt) return;
    if (ack?.ok !== true || ack.saved !== true || ack.id !== reference) throw new Error('Save not confirmed');
    const savedReference = reference; reference = '';
    form.reset(); updateOptional();
    document.getElementById('receipt-reference').textContent = `문의 참조번호: ${savedReference}`;
    status.textContent = '이사 문의가 접수되었습니다. 내용을 확인한 뒤 연락드리겠습니다.';
    dialog.showModal(); window.scrollTo(0, 0); tellParent('ok-express-form-saved');
  } catch {
    if (current === attempt) failure('접수 완료를 확인하지 못했습니다. 입력 내용은 유지됩니다. 다시 시도하거나 전화로 확인해 주세요.');
  } finally {
    clearTimeout(timer);
    if (current === attempt) { pending = false; fields.disabled = false; submit.disabled = false; form.removeAttribute('aria-busy'); submit.textContent = '이사 문의 접수하기 ↗'; }
  }
});
init();
