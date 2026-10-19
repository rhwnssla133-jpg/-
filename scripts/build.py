#!/usr/bin/env python3
"""Dependency-free static build. All business data is read from config.json."""
import argparse
import datetime
import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def confirmed(value):
    return bool(value) and str(value).strip() not in {"확인 필요", "확인 중", "미정"}


def readiness(config):
    missing = []
    for key in ("representative", "registrationNumber", "address", "transportPermit", "openingHours", "insuranceDetails"):
        if not confirmed(config["business"].get(key)):
            missing.append("business." + key)
    for key in ("responsiblePerson", "department", "manualDeletionProcedureConfirmed", "noticeReviewedOn"):
        if not confirmed(config["privacy"].get(key)):
            missing.append("privacy." + key)
    google = config.get('integrations', {}).get('googleSheets', {})
    for key in ('onlineRequested', 'contractAndCompensationReviewedOn'):
        if not confirmed(config['operation'].get(key)):
            missing.append('operation.' + key)
    if not google.get('requested'):
        missing.append('integrations.googleSheets.requested')
    if google.get('requested'):
        for key in ('deliveryConfigured', 'privacyReviewedOn'):
            if not confirmed(google.get(key)):
                missing.append('integrations.googleSheets.' + key)
        gt = google.get('transfer', {})
        for key in ('recipientLegalName', 'recipientContact', 'countries', 'subprocessors', 'items', 'time', 'method', 'purpose', 'retention', 'dpaUrl', 'verifiedOn'):
            value = gt.get(key)
            if not confirmed(value) or (isinstance(value, list) and not all(confirmed(x) for x in value)):
                missing.append('integrations.googleSheets.transfer.' + key)
    endpoint = google.get('webAppUrl')
    if not confirmed(endpoint):
        missing.append('integrations.googleSheets.webAppUrl')
    elif not re.fullmatch(r'https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec', endpoint):
        raise ValueError('Google webAppUrl must be an HTTPS script.google.com /exec deployment URL')
    for key in ("effectiveDate", "url"):
        if not confirmed(config["site"].get(key)):
            missing.append("site." + key)
    # HTTPS origin only. Never publish example domains or arbitrary URL paths.
    url = config["site"].get("url")
    if url:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("site.url must be an HTTPS origin, e.g. https://your-site.netlify.app")
    if config["privacy"]["retentionDays"] != 90:
        raise ValueError("보유기간 변경은 안내문과 삭제 절차를 함께 검토해야 합니다. 현재 지원값은 90일입니다.")
    return missing


def template(name, values):
    content = (ROOT / "src/templates" / name).read_text(encoding="utf-8")
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise KeyError(f"Unknown template variable: {key}")
        return str(values[key])
    return re.sub(r"\{\{(\w+)\}\}", replace, content)


def table(rows):
    return '<table class="legal-table"><tbody>' + ''.join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{v}</td></tr>" for k, v in rows) + '</tbody></table>'


def pending(value):
    if not value:
        return "확인 중 — 온라인 문의 접수 전 확정"
    if isinstance(value, list):
        return "<br>".join(esc(x) for x in value)
    return esc(value)


def form_markup(c, ready):
    b = c["business"]
    # Shared markup: an inert local fallback and the Google-hosted form.
    return f'''<form name="ok-express-inquiry" id="inquiry-form" method="POST" data-ready="{str(ready).lower()}" data-origin="{esc((c['site']['url'] or '').rstrip('/'))}" novalidate>
<input type="hidden" name="consent-version" value="{esc(c['site']['policyVersion'])}">
<input type="hidden" name="inquiry-reference" value="">
<p class="honeypot" aria-hidden="true"><label>이 항목은 입력하지 마세요<input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
<div class="error-summary" id="error-summary" role="alert" tabindex="-1"></div>
<fieldset class="form-fields" id="inquiry-fields" disabled><legend class="honeypot">이사 문의 내용</legend>
<div class="form-row"><div class="field"><label for="phone">연락 가능한 전화번호 <b>*</b><small>필수</small></label><input id="phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" required maxlength="20" placeholder="010-0000-0000" aria-describedby="phone-error"><p class="field-error" id="phone-error"></p></div><div class="field"><label for="move-type">이사 종류 <b>*</b><small>필수</small></label><select id="move-type" name="move-type" required aria-describedby="move-type-error"><option value="">선택해 주세요</option><option>포장이사</option><option>일반이사</option><option>사무실이사</option></select><p class="field-error" id="move-type-error"></p></div></div>
<div class="form-row"><div class="field"><label for="origin-area">출발 지역 <b>*</b><small>필수</small></label><input id="origin-area" name="origin-area" required maxlength="60" placeholder="예: 광주 북구 용봉동" aria-describedby="area-help origin-area-error" autocomplete="off"><p class="field-error" id="origin-area-error"></p></div><div class="field"><label for="destination-area">도착 지역 <b>*</b><small>필수</small></label><input id="destination-area" name="destination-area" required maxlength="60" placeholder="예: 광주 광산구 수완동" aria-describedby="area-help destination-area-error" autocomplete="off"><p class="field-error" id="destination-area-error"></p></div></div>
<p class="form-help" id="area-help">시·구·동까지만 입력해 주세요. 상세주소·동호수·공동현관 비밀번호는 입력하지 마세요.</p>
<div class="field"><label class="checkbox-line" for="optional-consent"><input id="optional-consent" name="optional-consent" type="checkbox" value="agreed"><span><a href="/collection/#optional" target="_blank" rel="noopener">선택정보 수집·이용</a>에 동의합니다. (선택)</span></label><p class="consent-short">호칭·희망일·추가 요청사항 / 견적 상담·연락 / 목적 달성 시 파기, 미계약 문의 최대 90일. 거부해도 필수정보만으로 문의할 수 있습니다.</p></div>
<div class="form-row"><div class="field"><label for="customer-name">성함 또는 호칭 <small>선택</small></label><input id="customer-name" name="customer-name" maxlength="30" placeholder="불러드릴 호칭" autocomplete="off" disabled aria-describedby="customer-name-error"><p class="field-error" id="customer-name-error"></p></div><div class="field"><label for="move-date">이사 희망일 <small>선택</small></label><input id="move-date" name="move-date" type="date" disabled aria-describedby="move-date-error"><p class="field-error" id="move-date-error"></p></div></div>
<div class="field"><label class="checkbox-line" for="date-undecided"><input id="date-undecided" name="date-undecided" type="checkbox" value="undecided" disabled><span>이사 날짜 미정 (선택)</span></label></div>
<div class="field"><label for="message">추가 요청사항 <small>선택 · 최대 500자</small></label><textarea id="message" name="message" maxlength="500" rows="3" placeholder="짐의 양, 층수, 승강기 유무 등 알려주실 내용을 적어주세요." disabled aria-describedby="message-help message-error"></textarea><p class="field-error" id="message-error"></p></div><p class="form-help" id="message-help">주민등록번호·계좌번호·상세주소·비밀번호 등 민감하거나 불필요한 정보는 적지 마세요. 사진·이메일은 수집하지 않습니다.</p>
<div class="consent-area"><div class="field"><label class="checkbox-line" for="required-consent"><input id="required-consent" name="required-consent" type="checkbox" value="agreed" required aria-describedby="required-consent-error"><span><a href="/collection/" target="_blank" rel="noopener">필수 개인정보 수집·이용</a>에 동의합니다. (필수)</span></label><p class="consent-short">수집 주체: {esc(b['name'])} / 전화번호·이사 종류·출발·도착 지역 / 견적 상담·연락 / 목적 달성 시 파기, 미계약 문의 최대 90일. 동의 거부 시 온라인 접수가 제한됩니다.</p><p class="field-error" id="required-consent-error"></p></div>
<div class="field"><label class="checkbox-line" for="overseas-consent"><input id="overseas-consent" name="overseas-consent" type="checkbox" value="agreed" required aria-describedby="overseas-consent-error"><span><a href="/privacy/#overseas" target="_blank" rel="noopener">개인정보 국외이전 안내</a>를 확인하고 별도 동의합니다. (필수)</span></label><p class="consent-short">온라인 문의는 국외에서 처리·보관될 수 있습니다. 이전 항목·국가·수탁자·연락처·시기·방법·목적·기간을 안내에서 확인해 주세요. 거부 시 <a href="{esc(b['phoneLink'])}">전화 상담</a>을 이용할 수 있습니다.</p><p class="field-error" id="overseas-consent-error"></p></div></div>
<button class="button button-orange form-submit" id="submit-inquiry" type="submit">이사 문의 접수하기 <span aria-hidden="true">↗</span></button></fieldset><p class="form-status" id="form-status" role="status" aria-live="polite"></p></form>'''


def build(config_path, output):
    c = json.loads(Path(config_path).read_text(encoding="utf-8"))
    missing = readiness(c)
    ready = not missing
    b, s, p = c["business"], c["site"], c["privacy"]
    values = {"name": esc(b['name']), "tagline": esc(b['tagline']), "phone": esc(b['phone']), "phoneLink": esc(b['phoneLink']), "email": esc(b['inquiryEmail']), "year": "2026"}
    details = [esc(b['region'])]
    for label, key in [("대표", "representative"), ("사업자등록번호", "registrationNumber"), ("사업장", "address"), ("운송·주선 허가", "transportPermit")]:
        if b[key]:
            details.append(esc(label + " " + b[key]))
    if not all(b[k] for k in ("representative", "registrationNumber", "address", "transportPermit")):
        details.append("사업자 상세정보 확인 중 · 현재 전화 문의 가능")
    values['businessDetails'] = " · ".join(details)
    values['header'] = template('header.html', values)
    values['footer'] = template('footer.html', values)
    out = Path(output).resolve()
    # Refuse dangerous cleanup, including either an ancestor or a child of sources.
    if out in [ROOT, ROOT.parent, Path('/')] or ROOT / 'src' == out or ROOT / 'src' in out.parents or out in (ROOT / 'src').parents:
        raise ValueError('Unsafe output path')
    if out.exists():
        marker = out / '.ok-express-build'
        if not marker.exists():
            raise ValueError(f'Refusing to overwrite an unrecognized directory: {out}')
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / '.ok-express-build').write_text('generated static files\n')
    shutil.copytree(ROOT / 'src/assets', out / 'assets', ignore=shutil.ignore_patterns('google-form.js', 'validation.js'))

    def page(path, title, content, description=None, noindex=False):
        seo = '<meta name="robots" content="noindex, nofollow">' if noindex else ''
        if s['url'] and not noindex:
            url = s['url'].rstrip('/') + path
            seo += f'<link rel="canonical" href="{esc(url)}"><meta property="og:url" content="{esc(url)}">'
        data = {**values, 'title': esc(title), 'description': esc(description or s['description']), 'content': content, 'seo': seo}
        target = out / path.strip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(template('layout.html', data), encoding='utf-8')

    box = '<svg viewBox="0 0 80 80" fill="none"><path d="m10 24 30-15 30 15v34L40 74 10 58z" fill="#fff0de" stroke="#172b40" stroke-width="2"/><path d="m10 24 30 16 30-16M40 40v34M26 16l29 16v15l-12 6V37L15 21" stroke="#172b40" stroke-width="2"/><path d="m26 16 29 16-12 5-28-16z" fill="#f39158"/></svg>'
    truck = '<svg viewBox="0 0 80 80" fill="none"><path d="M6 20h43v40H6z" fill="#fff0de" stroke="#172b40" stroke-width="2"/><path d="M49 33h14l12 15v12H49z" fill="#f39158" stroke="#172b40" stroke-width="2"/><path d="M54 39h7l8 10H54z" fill="white" stroke="#172b40" stroke-width="2"/><circle cx="21" cy="61" r="8" fill="#172b40"/><circle cx="61" cy="61" r="8" fill="#172b40"/><circle cx="21" cy="61" r="3" fill="white"/><circle cx="61" cy="61" r="3" fill="white"/><path d="M14 30h20M14 36h12" stroke="#172b40" stroke-width="2"/></svg>'
    office = '<svg viewBox="0 0 80 80" fill="none"><path d="M17 10h45v62H17z" fill="#fff0de" stroke="#172b40" stroke-width="2"/><path d="M26 21h8v9h-8zm20 0h8v9h-8zM26 39h8v9h-8zm20 0h8v9h-8z" fill="#f39158" stroke="#172b40" stroke-width="2"/><path d="M33 72V58h14v14M8 72h63" stroke="#172b40" stroke-width="2"/></svg>'
    care = '<svg viewBox="0 0 140 150" fill="none"><path d="M70 12c19 12 37 14 50 15v39c0 32-24 56-50 69-26-13-50-37-50-69V27c13-1 31-3 50-15Z" fill="#f5f4e9" stroke="#47626b" stroke-width="2"/><path d="m45 74 17 17 34-37" stroke="#e77a43" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><path d="m13 39-8-5m126 5 8-5M27 121l-8 6m95-6 8 6" stroke="#8a9d9c" stroke-width="2" stroke-linecap="round"/></svg>'
    available = '이사 조건을 남겨주시면 내용을 확인한 뒤 연락드리겠습니다.' if ready else f'온라인 문의를 준비하고 있습니다. 지금은 <a href="{values["phoneLink"]}">{values["phone"]}로 전화 문의해 주세요.</a>'
    local_form = form_markup(c, False)
    if ready:
        local_form = f'<iframe id="google-inquiry" class="google-inquiry" title="이사 견적 문의 입력 폼" data-url="{esc(c["integrations"]["googleSheets"]["webAppUrl"])}" data-origin="{esc(s["url"].rstrip("/"))}" data-ready="true" hidden></iframe><p id="google-form-status" class="form-help" role="status">문의창을 불러오고 있습니다. 잠시 기다려 주세요.</p><p class="form-help"><a href="{esc(c["integrations"]["googleSheets"]["webAppUrl"])}" target="_blank" rel="noopener noreferrer">별도 문의창 열기</a> · 문의창 이용이 어려우면 <a href="{values["phoneLink"]}">{values["phone"]}로 전화해 주세요.</a></p>'
    home = template('home.html', {**values, 'boxIcon': box, 'truckIcon': truck, 'officeIcon': office, 'careIcon': care, 'availabilityMessage': available, 'form': local_form})
    page('/', '광주 포장이사 OK익스프레스 | 일반이사·사무실이사', home)

    def legal(title, eyebrow, intro, body):
        return f'<main id="main"><section class="legal-hero"><div class="container"><p class="eyebrow section-label">{eyebrow}</p><h1>{title}</h1><p>{intro}</p></div></section><article class="container legal-body">{body}</article></main>'

    status = '' if ready else '<p class="notice">현재 온라인 문의는 받지 않습니다. 아래 안내의 확인 중인 항목을 확정한 뒤 온라인 접수를 시작합니다. 지금은 전화 상담을 이용해 주세요.</p>'
    keep = '상담 목적 달성 시 지체 없이 파기하며, 미계약 문의는 접수일부터 최대 90일간 보관합니다.'
    collect_body = status + '<h2>1. 수집 주체와 목적</h2><p>' + values['name'] + '는 이사 견적 상담과 연락을 위해 아래 정보를 수집·이용합니다. 광고·마케팅 목적으로 이용하지 않습니다.</p>'
    collect_body += table([('수집 주체', values['name']), ('목적', '이사 조건 확인, 견적 상담 및 연락'), ('필수 항목', '연락 가능한 전화번호, 이사 종류, 출발 지역, 도착 지역'), ('선택 항목', '성함 또는 호칭, 이사 희망일 또는 미정 여부, 추가 요청사항'), ('동의 기록', '필수 수집·이용 동의, 선택정보 동의, 별도 국외이전 동의 여부와 동의문 버전, 문의 참조번호. 접수 시각은 Google 문의 처리 시 기록합니다.'), ('보유기간', keep)])
    collect_body += '<h2>2. 필수정보 동의와 거부권</h2><p>필수정보 수집·이용에 동의하지 않을 수 있습니다. 거부 시 온라인 견적 문의 접수가 제한됩니다. 전화 상담을 이용할 수 있습니다.</p><h2 id="optional">3. 선택정보 동의와 거부권</h2><p>선택정보 동의는 필수 동의와 분리되어 있으며 기본 미선택입니다. 선택 동의 없이도 필수정보만으로 문의할 수 있고, 선택정보 입력값은 전송하지 않습니다. 선택 동의를 해제하면 입력값을 지우며, 다시 동의하더라도 복원하지 않습니다.</p><h2>4. 국외이전과 처리 위탁</h2><p>온라인 문의는 Google이 제공하는 문의창에서 직접 입력받아 Google 스프레드시트에 기록하고 운영자의 Google 이메일로 알립니다. 정적 홈페이지 제공자는 문의 원본을 접수하지 않으며, Google에서 국외 처리·보관될 수 있습니다. 수집·이용 동의와 별개로 <a href="/privacy/#overseas">국외이전 상세 안내</a>를 확인하고 동의해야 합니다. 미확정 항목이 남아 있는 동안 온라인 접수를 제공하지 않습니다.</p><h2>5. 문의와 권리 행사</h2>'
    collect_body += f'<p>열람·정정·삭제·동의 철회는 <a href="{values["phoneLink"]}">{values["phone"]}</a> 또는 <a href="mailto:{values["email"]}">{values["email"]}</a>로 요청할 수 있습니다. 추가 본인 확인이 필요한 경우 필요한 범위에서 안내합니다.</p><p><a href="/privacy/">개인정보처리방침 전체 보기</a> · <a href="/#inquiry">견적 문의로 돌아가기</a></p>'
    page('/collection/', '개인정보 수집·이용 안내 | ' + b['name'], legal('개인정보 수집·이용 안내', 'YOUR INFORMATION', '문의 전에 수집 항목과 이용 목적, 동의 거부권을 확인해 주세요.', collect_body))

    t = c['integrations']['googleSheets']['transfer']
    privacy_body = status + f'<p class="legal-meta">문서 버전: {esc(s["policyVersion"])} · 시행일: {esc(s["effectiveDate"] or "온라인 접수 개시 전 확정")}</p><h2>1. 개인정보 처리 주체</h2>'
    privacy_body += table([('상호 / 지역', values['name'] + ' / ' + esc(b['region'])), ('대표자 / 사업장', pending(b['representative']) + ' / ' + pending(b['address'])), ('개인정보 담당자', pending(p['responsiblePerson'])), ('담당 부서', pending(p['department'])), ('연락처', f'<a href="{values["phoneLink"]}">{values["phone"]}</a> · <a href="mailto:{values["email"]}">{values["email"]}</a>')])
    privacy_body += '<h2>2. 처리 목적·항목·수집 방법</h2><p>고객이 온라인 문의 폼에 직접 입력한 정보를 이사 견적 상담과 연락 목적으로만 처리합니다. 필수 항목은 전화번호·이사 종류·출발 지역·도착 지역입니다. 선택 동의 시 호칭·희망일 또는 미정 여부·추가 요청사항을 처리합니다. 동의 여부·동의문 버전·문의 참조번호·접수 시각과 처리·중복 확인용 값도 기록합니다. 선택 동의 없이 선택 입력값은 전송하지 않습니다.</p><p>사진 첨부, 고객 이메일, 주민등록번호, 계좌번호는 기본 문의에서 수집하지 않습니다. 상세 동·호수와 공동현관 비밀번호를 입력하지 마세요. 광고 추적 도구와 마케팅 발송 기능을 사용하지 않으며, 문의 내용을 URL이나 브라우저 저장소에 저장하지 않습니다. 서비스 제공자의 보안·접속 기록은 실제 서비스 설정과 DPA를 확인해 아래 위탁 안내에 반영해야 합니다.</p><h2>3. 보유기간</h2>'
    privacy_body += f'<p>{keep} 이 기간은 상담 운영을 위한 보유 기준이며 모든 문의의 법정 보유기간을 의미하지 않습니다.</p><p>계약으로 전환된 기록은 실제 적용되는 법적 근거·항목·기간을 확인해 필요한 범위만 별도로 보관합니다. 모든 문의를 일괄 5년 보관하지 않습니다.</p><h2>4. 파기 절차와 방법</h2><p>상담 종료 또는 보유기간 경과 시 담당자가 Google 시트 원본과 상담 관리 기록·이메일 사본·휴지통을 확인해 삭제합니다. 자동 삭제 기능은 구현되어 있지 않습니다. 전자 기록은 서비스가 제공하는 삭제 기능을 사용하고, 출력물은 분쇄 등 복구하기 어려운 방법으로 파기합니다. 서비스 제공자의 백업·최종 삭제 주기는 확인한 계약과 국외이전 보유기간에 따릅니다.</p><h2>5. 열람·정정·삭제·동의 철회</h2><p><a href="{values["phoneLink"]}">{values["phone"]}</a> 또는 <a href="mailto:{values["email"]}">{values["email"]}</a>로 요청해 주세요. 본인 확인 후 관계 법령에 따라 처리하고 결과를 안내합니다. 법령에 따른 보존 의무 등으로 제한되는 경우 그 근거와 사유를 안내합니다. 필요 이상의 신분증·주민등록번호를 요구하지 않습니다.</p><h2>6. 처리 위탁과 제3자 제공의 구분</h2><p>정적 홈페이지는 Netlify에서 제공하며 접속·보안 기록이 처리될 수 있습니다. 고객 문의는 Google 문의창에서 직접 받아 Google 스프레드시트와 운영자의 Google 이메일에서 처리합니다. 문의 원본을 Netlify Forms에 저장하지 않습니다. 서비스 제공을 위한 처리 위탁과 독립적인 마케팅 등 제3자의 목적을 위한 제공을 구분합니다. 운영자는 계정 접근권한과 삭제를 관리합니다. 실제 계약 주체·처리 범위·재위탁 현황과 적용되는 위탁 사항을 접수 개시 전에 확정합니다. 고객 동의 또는 법령상 근거 없이 별도 목적의 제3자 제공을 하지 않습니다.</p><h2 id="overseas">7. 국외이전 상세 안내와 별도 동의</h2><p>개인정보 보호법 제28조의8에 따른 별도 국외이전 동의 방식을 채택하는 초안입니다. 실제 배포일의 법령과 계정의 DPA·재위탁 현황을 확인해 아래 항목을 확정하고 적용 근거를 검토한 후 접수를 시작합니다. 국내에서만 처리한다고 표시하지 않습니다.</p>'
    privacy_body += table([('이전받는 자', pending(t['recipientLegalName'])), ('수탁자 연락처', pending(t['recipientContact'])), ('이전 국가', pending(t['countries'])), ('재위탁 수탁자·국가·업무', pending(t['subprocessors'])), ('이전 항목', pending(t['items'])), ('이전 시기', pending(t['time'])), ('이전 방법', pending(t['method'])), ('이전 목적', pending(t['purpose'])), ('보유·이용기간 및 삭제', pending(t['retention'])), ('확인 자료', f'<a href="{esc(t["dpaUrl"] or 'https://policies.google.com/privacy')}" rel="noopener noreferrer" target="_blank">DPA 확인 자료</a> · <a href="{esc(t["dpaUrl"] or 'https://policies.google.com/privacy')}" rel="noopener noreferrer" target="_blank">재위탁 확인 자료</a>'), ('최종 확인일', pending(t['verifiedOn']))])
    privacy_body += f'<p>국외이전에 동의하지 않을 권리가 있으며, 동의하지 않으면 온라인 문의가 제한됩니다. <a href="{values["phoneLink"]}">{values["phone"]} 전화 상담</a>을 이용할 수 있습니다. 동의는 수집·이용 동의와 분리된 미선택 체크박스로 받습니다. 선택정보를 입력하면 별도 동의한 항목에 한해 이전 대상에 포함됩니다.</p><h2>8. 안전조치</h2><p>배포 환경에서는 HTTPS 통신을 사용합니다. 문의 관리자와 메일 계정의 접근권한을 최소화하고, 강력한 비밀번호와 다중 인증을 설정하며, 접근자와 보유기간을 정기 점검하는 운영 절차를 적용해야 합니다. 사이트에는 외부 광고·분석 스크립트를 넣지 않았습니다. 계정 보안과 삭제 절차의 실제 적용 여부는 운영자가 확인합니다.</p><h2>9. 방침 변경과 시행일</h2><p>처리 내용이 바뀌면 방침과 동의문 버전을 함께 변경하고 시행일을 게시합니다. 별도 동의가 필요한 변경은 관계 법령에 따라 안내하고 동의받습니다.</p><p><a href="/collection/">수집·이용 요약 보기</a> · <a href="/#inquiry">견적 문의로 돌아가기</a></p>'
    page('/privacy/', '개인정보처리방침 | ' + b['name'], legal('개인정보처리방침', 'PRIVACY & YOUR RIGHTS', '개인정보를 어떻게 처리하고, 어떤 권리를 행사할 수 있는지 안내합니다.', privacy_body))

    compensation_body = f'<p class="notice">이사 과정에서 물품의 파손이나 분실이 의심되면 <a href="{values["phoneLink"]}">{values["phone"]}</a>로 알려주세요.</p><h2>1. 사고 접수</h2><p>해당 물품과 현장 상태를 사진으로 남기고, 물품명·모델명·구입 시기·구입가격을 확인할 수 있는 자료를 준비해 주시면 확인에 도움이 됩니다. 영수증이 없는 경우에도 확인 가능한 대체 자료를 함께 검토합니다.</p><h2>2. 사실 확인</h2><p>사고 경위와 물품 상태를 확인한 뒤 적용 법령과 계약 내용에 따라 책임 범위와 처리 방법을 안내합니다. 자료 요청은 사실 확인을 돕기 위한 것이며 법정 입증책임을 고객에게 일방적으로 전가하지 않습니다.</p><h2>3. 처리 결과와 배상 방법 안내</h2><p>업체의 배상책임이 인정되는 경우 수리가 가능한 물품은 수선하고, 수리가 불가능하거나 분실된 물품은 관련 기준에 따른 물품 가액 등을 검토해 배상합니다. 사용기간과 기존 상태 등을 고려할 수 있으며, 산정 근거와 처리 방법을 안내합니다.</p><p>보험 가입·보장 범위는 확인되지 않았으며 특정 보험이나 보장금액을 약속하지 않습니다. 실제 보험이 적용되는 경우에도 보험 한도가 업체의 모든 법적 책임 한도와 같다는 의미는 아닙니다.</p><h2>4. 이사 전에 준비해 주세요</h2><p>현금·귀금속·중요서류 등 휴대 가능한 귀중품은 직접 보관해 주시고, 고가품·특수물품은 계약 전에 운송 조건을 협의해 주세요.</p><h2>5. 발견 시 연락과 고객의 권리</h2><p>빠른 현장 확인을 위해 발견 즉시 연락을 권장하며, 이 안내로 관계 법령과 적용 약관에 따른 고객의 권리를 제한하지 않습니다. 당일 미신고, 고객 포장, 잔금 지급, 영수증 부재만으로 청구를 일괄 배제하지 않습니다.</p><p>이사화물 표준약관은 실제 계약에 적법하게 채택·교부되었는지 확인해야 하며, 이 홈페이지가 자동 적용을 뜻하지 않습니다. 표준약관의 일부 분실·훼손 관련 30일 통지 기준은 모든 청구에 공통된 소멸시효와 구분해야 합니다. 은폐 등 예외와 별도 책임 소멸기간도 적용 법령·약관의 현행 내용과 실제 계약을 확인해 판단합니다. 이 안내는 별도의 신고기한이나 면책 조건을 정하지 않습니다.</p><h2>6. 계약 내용과 확인 자료</h2><p>최종 견적, 작업 범위, 물품 상태, 변경 합의, 사고 접수와 처리 내용을 서로 확인할 수 있도록 남겨 주세요. 홈페이지 안내와 계약 내용은 함께 확인하며, 관계 법령에 따른 고객의 권리가 우선합니다.</p><ul><li><a href="https://www.ftc.go.kr/www/selectBbsNttView.do?bordCd=201&amp;key=202&amp;nttSn=11148" target="_blank" rel="noopener noreferrer">공정거래위원회 이사화물 표준약관 확인</a></li><li><a href="https://www.easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=3&amp;cciNo=1&amp;cnpClsNo=1&amp;csmSeq=629&amp;popMenu=ov" target="_blank" rel="noopener noreferrer">찾기 쉬운 생활법령: 이사 분쟁 안내</a></li></ul><p>실제 계약에 적용되는 약관과 법령은 계약 시점에 확인합니다. 확인되지 않은 처리기한이나 전액 보상을 약속하지 않습니다.</p><p><a href="{values["phoneLink"]}">파손·분실 전화 접수 {values["phone"]}</a> · <a href="/#inquiry">이사 문의</a></p>'
    page('/compensation/', '파손·분실 접수 및 보상 안내 | ' + b['name'], legal('파손·분실 접수 및 보상 안내', 'CARE AFTER MOVING', '접수 → 사실 확인 → 처리 결과 안내. 상황을 확인하고 책임 범위와 처리 방법을 안내합니다.', compensation_body))

    # A directly opened thank-you URL is never evidence of a successful submission.
    thanks = f'<main id="main" class="success-page"><div class="container"><p class="eyebrow section-label">{values["name"]}</p><h1>이사 문의 안내</h1><p>이 페이지를 여는 것만으로 문의가 접수되지는 않습니다.<br>온라인 문의 폼을 이용하거나 전화로 연락해 주세요.</p><div class="hero-actions"><a class="button button-orange" href="/#inquiry">견적 문의로 이동</a><a class="button button-outline" href="{values["phoneLink"]}">전화 문의</a></div></div></main>'
    page('/thank-you/', '이사 문의 안내 | ' + b['name'], thanks, noindex=True)
    not_found = f'<main id="main" class="success-page"><div class="container"><p class="eyebrow section-label">404</p><h1>페이지를 찾을 수 없습니다.</h1><p>주소를 확인하거나 홈에서 필요한 안내를 찾아주세요.</p><a class="button button-orange" href="/">홈으로 이동</a></div></main>'
    page('/404/', '페이지를 찾을 수 없습니다 | ' + b['name'], not_found, noindex=True)
    shutil.copyfile(out / '404/index.html', out / '404.html')
    shutil.rmtree(out / '404')
    paths = ['/', '/collection/', '/privacy/', '/compensation/']
    if s['url']:
        urls = ''.join('<url><loc>' + esc(s['url'].rstrip('/') + path) + '</loc></url>' for path in paths)
        (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>', encoding='utf-8')
    robots = 'User-agent: *\nAllow: /\nDisallow: /thank-you/\n'
    if s['url']:
        robots += 'Sitemap: ' + s['url'].rstrip('/') + '/sitemap.xml\n'
    (out / 'robots.txt').write_text(robots)
    # Same security policy for ZIP drag-and-drop deploys, which do not run a build.
    (out / '_headers').write_text("""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; frame-src https://script.google.com https://script.googleusercontent.com https://*.googleusercontent.com
/thank-you/*
  X-Robots-Tag: noindex, nofollow
  Cache-Control: no-store
""", encoding='utf-8')
    print(f'Built {out}; online inquiry: {"ENABLED" if ready else "LOCKED"}')
    if missing:
        print('확인 필요: ' + ', '.join(missing))
    return missing


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.config, args.output)
