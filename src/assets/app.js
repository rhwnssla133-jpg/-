// No analytics, local/session storage, console payloads, or third-party scripts.
export function seoulDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const part = (type) => parts.find((p) => p.type === type).value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export function normalizePhone(value) {
  return value.replace(/[\s()-]/g, '').replace(/^\+82/, '0');
}

export function validateInquiry(values, today = seoulDate()) {
  const errors = {};
  const phone = normalizePhone(values.phone || '');
  if (!values.phone?.trim()) errors.phone = '연락 가능한 전화번호를 입력해 주세요.';
  else if (values.phone.length > 20 || !/^(?:010\d{8}|01[16789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8}|050\d{8,9})$/.test(phone)) errors.phone = '전화번호 형식을 확인해 주세요. 예: 010-0000-0000';
  if (!['포장이사', '일반이사', '사무실이사'].includes(values['move-type'])) errors['move-type'] = '이사 종류를 선택해 주세요.';
  for (const [key, label] of [['origin-area', '출발 지역'], ['destination-area', '도착 지역']]) {
    const area = (values[key] || '').trim();
    if (!area) errors[key] = `${label}을 시·구·동 수준으로 입력해 주세요.`;
    else if (area.length > 60) errors[key] = `${label}은 60자 이내로 입력해 주세요.`;
    else if (/(?:\d+\s*(?:호|번지)|(?:^|\s)\d{2,4}동(?:\s|$)|\d{1,4}-\d{1,4}|(?:로|길)\s*\d+|비밀번호|공동현관)/.test(area)) errors[key] = '상세주소·동호수·비밀번호를 빼고 시·구·동까지만 입력해 주세요.';
  }
  if (values['required-consent'] !== 'agreed') errors['required-consent'] = '필수 개인정보 수집·이용 동의가 필요합니다.';
  if (values['overseas-consent'] !== 'agreed') errors['overseas-consent'] = '국외이전 안내를 확인하고 별도로 동의해 주세요.';
  if (values['optional-consent'] === 'agreed') {
    if ((values['customer-name'] || '').length > 30) errors['customer-name'] = '성함 또는 호칭은 30자 이내로 입력해 주세요.';
    if ((values.message || '').length > 500) errors.message = '추가 요청사항은 500자 이내로 입력해 주세요.';
    const date = values['move-date'];
    if (date && values['date-undecided'] !== 'undecided') {
      const parsed = new Date(`${date}T00:00:00Z`);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date) errors['move-date'] = '올바른 날짜를 입력해 주세요.';
      else if (date < today) errors['move-date'] = '오늘 이후의 날짜를 선택하거나 미정으로 표시해 주세요.';
    }
  }
  return errors;
}

function setupNavigation() {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.getElementById('navigation');
  if (!toggle || !nav) return;
  function close() { toggle.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); }
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) close(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && nav.classList.contains('is-open')) { close(); toggle.focus(); } });
  document.addEventListener('click', (event) => { if (!event.target.closest('.header-inner')) close(); });
  // Keep the toolbar hidden for the whole form interaction, including a submit
  // button taking focus. Otherwise it can reappear between pointerdown and click.
  const keyboard = () => document.body.classList.toggle('keyboard-open', !!document.activeElement?.closest('#inquiry-form'));
  document.addEventListener('focusin', keyboard);
  document.addEventListener('focusout', () => setTimeout(keyboard, 0));
}

function setupForm() {
  const form = document.getElementById('inquiry-form');
  if (!form) return;
  const fields = document.getElementById('inquiry-fields');
  const status = document.getElementById('form-status');
  const submit = document.getElementById('submit-inquiry');
  const summary = document.getElementById('error-summary');
  const consent = document.getElementById('optional-consent');
  const optionalNames = ['customer-name', 'move-date', 'date-undecided', 'message'];
  const dialog = document.getElementById('success-dialog');
  const configured = form.dataset.ready === 'true' && location.protocol === 'https:' && location.origin === form.dataset.origin;
  let pending = false;
  let reference = '';
  fields.disabled = !configured;
  if (form.dataset.ready === 'true' && !configured) {
    const notice = document.getElementById('availability-notice');
    notice.textContent = '이 화면에서는 온라인 문의를 접수하지 않습니다. 전화로 문의해 주세요.';
    submit.textContent = '전화로 문의해 주세요';
  } else if (!configured) {
    submit.textContent = '현재 전화 문의만 가능합니다';
  }
  const get = (name) => form.elements.namedItem(name);
  const updateOptional = () => {
    for (const name of optionalNames) {
      const input = get(name);
      input.disabled = !configured || !consent.checked;
      if (!consent.checked) { if (input.type === 'checkbox') input.checked = false; else input.value = ''; }
    }
    const undecided = get('date-undecided');
    if (consent.checked && undecided.checked) { get('move-date').value = ''; get('move-date').disabled = true; }
    clearErrors(optionalNames);
  };
  function clearErrors(names) {
    for (const name of names) {
      get(name)?.removeAttribute('aria-invalid');
      const target = document.getElementById(`${name}-error`);
      if (target) target.textContent = '';
    }
  }
  function showErrors(errors) {
    summary.replaceChildren();
    const title = document.createElement('strong'); title.textContent = '입력한 내용을 확인해 주세요.';
    const list = document.createElement('ul');
    for (const [name, message] of Object.entries(errors)) {
      get(name).setAttribute('aria-invalid', 'true');
      document.getElementById(`${name}-error`).textContent = message;
      const li = document.createElement('li'); const link = document.createElement('a');
      link.href = `#${name}`; link.textContent = message;
      link.addEventListener('click', (event) => { event.preventDefault(); get(name).focus(); });
      li.append(link); list.append(li);
    }
    summary.append(title, list); summary.focus();
  }
  function showFailure() {
    status.replaceChildren();
    const text = document.createTextNode('접수 완료를 확인하지 못했습니다. 입력 내용은 유지됩니다. 통신 중단 시 이미 접수되었을 수도 있으니 전화로 확인하거나 다시 시도해 주세요. ');
    const phone = document.querySelector('.footer-phone');
    const link = document.createElement('a'); link.href = phone.href; link.textContent = '전화 문의';
    status.append(text, link);
  }
  consent.addEventListener('change', updateOptional);
  get('date-undecided').addEventListener('change', updateOptional);
  get('move-date').min = seoulDate();
  updateOptional();
  document.querySelectorAll('[data-service]').forEach((link) => link.addEventListener('click', () => { if (configured) get('move-type').value = link.dataset.service; }));
  document.getElementById('close-success').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => submit.focus({ preventScroll: true }));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!configured || pending) return;
    summary.replaceChildren();
    clearErrors(['phone', 'move-type', 'origin-area', 'destination-area', 'customer-name', 'move-date', 'message', 'required-consent', 'overseas-consent']);
    status.textContent = '';
    const data = new FormData(form);
    const values = Object.fromEntries(data.entries());
    // Explicit allowlist. Never forward optional values without separate consent.
    const errors = validateInquiry(values);
    if (Object.keys(errors).length) { showErrors(errors); return; }
    if (data.get('bot-field')) { status.textContent = '접수할 수 없습니다. 전화로 문의해 주세요.'; return; }
    const body = new URLSearchParams();
    for (const name of ['form-name', 'consent-version', 'bot-field', 'move-type', 'origin-area', 'destination-area', 'required-consent', 'overseas-consent']) body.set(name, String(data.get(name) || '').trim());
    body.set('phone', normalizePhone(values.phone));
    body.set('optional-consent', consent.checked ? 'agreed' : 'not-agreed');
    if (consent.checked) {
      for (const name of optionalNames) { const value = data.get(name); if (value) body.set(name, String(value).trim()); }
    }
    reference ||= `OK-${crypto.randomUUID()}`;
    get('inquiry-reference').value = reference;
    body.set('inquiry-reference', reference);
    body.set('subject', `${get('subject').defaultValue} · ${reference}`);
    pending = true; fields.disabled = true; submit.disabled = true; form.setAttribute('aria-busy', 'true');
    submit.textContent = '문의 내용을 보내고 있습니다…'; status.textContent = '접수 응답을 기다리고 있습니다.';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    let succeeded = false;
    try {
      const response = await fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: body.toString(), credentials: 'same-origin', signal: controller.signal });
      if (!response.ok || response.type === 'opaque' || (response.url && new URL(response.url).origin !== location.origin)) throw new Error('Submission not confirmed');
      succeeded = true;
      form.reset(); updateOptional();
      document.getElementById('receipt-reference').textContent = `문의 참조번호: ${reference}`;
      reference = '';
      status.textContent = '이사 문의가 접수되었습니다. 내용을 확인한 뒤 연락드리겠습니다.';
    } catch {
      // Do not log requests or errors containing customer data.
      showFailure();
    } finally {
      clearTimeout(timeout); pending = false; fields.disabled = false; submit.disabled = false;
      form.removeAttribute('aria-busy'); submit.textContent = '이사 문의 접수하기 ↗';
    }
    if (succeeded) dialog.showModal();
  });
}

setupNavigation();
setupForm();
