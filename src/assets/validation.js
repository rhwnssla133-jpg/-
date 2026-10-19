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

