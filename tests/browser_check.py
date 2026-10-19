"""Real Chromium checks with in-memory mocked Netlify responses, NOT a live receipt test."""
import asyncio
import json
import mimetypes
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright
from test_build import ROOT, builder, fixture_config


async def main():
    results = []
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ok-express-test-') as folder:
        fixture = Path(folder) / 'fixture.json'
        fixture.write_text(json.dumps(fixture_config()))
        test_site = Path(folder) / 'site'
        builder.build(fixture, test_site)
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True, args=['--no-sandbox'])
            context = await browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='ko-KR', timezone_id='Asia/Seoul', reduced_motion='reduce')
            page = await context.new_page()
            runtime_errors = []
            page.on('pageerror', lambda error: runtime_errors.append(str(error)))
            state = {'fixture': False, 'mode': 'success', 'posts': [], 'release': None}

            async def route_request(route):
                request = route.request
                url = urlsplit(request.url)
                if request.method == 'POST':
                    assert state['fixture'], 'Production-default page must never submit'
                    assert url.path == '/thank-you/'
                    state['posts'].append(parse_qs(request.post_data or '', keep_blank_values=True))
                    if state['mode'] == 'network-failure':
                        await route.abort('failed')
                    elif state['mode'] == 'http-failure':
                        await route.fulfill(status=503, body='Test failure')
                    else:
                        if state['mode'] == 'delayed':
                            await state['release'].wait()
                        await route.fulfill(status=200, content_type='text/html', body='Synthetic Netlify response, not a live submission')
                    return
                assert request.method == 'GET'
                root = test_site if state['fixture'] else ROOT / 'dist'
                relative = url.path.lstrip('/')
                target = root / relative
                if target.is_dir():
                    target = target / 'index.html'
                if not target.is_file():
                    await route.fulfill(status=404, body='Not found')
                    return
                await route.fulfill(status=200, content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream', body=target.read_bytes())

            await context.route('**/*', route_request)
            base = 'https://ok-express-fixture.netlify.app'
            await page.goto(base)
            await page.locator('.hero h1').wait_for()
            assert await page.locator('#inquiry-fields').evaluate('(element) => element.disabled')
            assert await page.locator('input[type=checkbox]:checked').count() == 0
            assert await page.locator('a[href^="tel:"]:not([href="tel:01025432424"])').count() == 0
            assert await page.locator('.hero-actions a[href="tel:01025432424"]').count() == 1
            await page.locator('.hero-actions a[href="#inquiry"]').click()
            assert urlsplit(page.url).fragment == 'inquiry'
            results.append('공개 기본 설정: 온라인 접수 잠금, 동의 기본 미선택, 전화 및 문의 이동')

            for width in [360, 390, 768, 1024, 1440]:
                await page.set_viewport_size({'width': width, 'height': 960})
                await page.evaluate('window.scrollTo(0,0)')
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow at {width}'
                if width == 360:
                    await page.screenshot(path=str(artifacts / 'homepage-mobile.png'), full_page=True)
                    await page.locator('.menu-toggle').click()
                    assert await page.locator('.menu-toggle').get_attribute('aria-expanded') == 'true'
                    await page.keyboard.press('Escape')
                    assert await page.locator('.menu-toggle').get_attribute('aria-expanded') == 'false'
                    assert await page.locator('.mobile-actions a').count() == 2
                elif width == 1440:
                    await page.screenshot(path=str(artifacts / 'homepage-desktop.png'), full_page=True)
            results.append('360·390·768·1024·1440px 가로 넘침 없음, 모바일 메뉴 및 Escape 닫기')

            for path, heading in [('/privacy/', '개인정보처리방침'), ('/collection/', '개인정보 수집·이용 안내'), ('/compensation/', '파손·분실 접수 및 보상 안내')]:
                await page.goto(base + path)
                assert await page.locator('h1').inner_text() == heading
                await page.set_viewport_size({'width': 360, 'height': 800})
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.goto(base + '/thank-you/')
            assert '이 페이지를 여는 것만으로' in await page.locator('main').inner_text()
            assert '이사 문의가 접수되었습니다.' not in await page.locator('main').inner_text()
            results.append('개인정보·수집 안내·보상 페이지 표시, 직접 연 감사 페이지는 가짜 성공 표시 안 함')

            state['fixture'] = True
            await page.goto(base)
            await page.locator('#inquiry-fields:not([disabled])').wait_for(state='attached')
            await page.locator('#submit-inquiry').click()
            assert await page.locator('#error-summary li').count() == 6
            assert await page.locator('#error-summary').evaluate('(element) => element === document.activeElement')
            await page.locator('#error-summary a').first.click()
            assert await page.locator('#phone').evaluate('(element) => element === document.activeElement')

            async def fill_required():
                await page.locator('#phone').fill('010-0000-0000')
                await page.locator('#move-type').select_option('포장이사')
                await page.locator('#origin-area').fill('광주 북구 용봉동')
                await page.locator('#destination-area').fill('광주 광산구 수완동')
                await page.locator('#required-consent').check()
                await page.locator('#overseas-consent').check()

            await fill_required()
            await page.locator('#phone').fill('123')
            await page.locator('#submit-inquiry').click()
            assert '전화번호 형식' in await page.locator('#phone-error').inner_text()
            assert len(state['posts']) == 0
            await fill_required()
            await page.locator('#origin-area').fill('광주 북구 101동 202호')
            await page.locator('#submit-inquiry').click()
            assert '상세주소' in await page.locator('#origin-area-error').inner_text()
            await fill_required()
            await page.locator('#optional-consent').check()
            await page.locator('#move-date').fill('2020-01-01')
            await page.locator('#submit-inquiry').click()
            assert '오늘 이후' in await page.locator('#move-date-error').inner_text()
            assert len(state['posts']) == 0
            # Test maximum lengths independently of native maxlength UI restriction.
            validation = await page.evaluate("""async () => {
              const { validateInquiry, seoulDate } = await import('/assets/app.js');
              const errors = validateInquiry({'phone':'01000000000','move-type':'포장이사','origin-area':'a'.repeat(61),'destination-area':'광주 북구','required-consent':'agreed','overseas-consent':'agreed','optional-consent':'agreed','customer-name':'a'.repeat(31),'message':'a'.repeat(501)}, '2026-10-19');
              return {errors, date:seoulDate(new Date('2026-10-18T15:01:00Z'))};
            }""")
            assert set(validation['errors']) == {'origin-area', 'customer-name', 'message'}
            assert validation['date'] == '2026-10-19'
            results.append('필수 누락·전화번호·상세주소·과거 날짜·길이 검증, 오류 요약 및 위치 포커스')

            await page.locator('#customer-name').fill('테스트 호칭')
            await page.locator('#message').fill('동의 거부 시 전송되면 안 되는 테스트 값')
            await page.locator('#optional-consent').uncheck()
            for name in ['customer-name', 'move-date', 'message']:
                assert await page.locator('#' + name).input_value() == ''
                assert await page.locator('#' + name).is_disabled()
            # Even a DOM-injected optional value must not enter the payload.
            await page.locator('#message').evaluate("element => {element.value='전송 금지 테스트';element.disabled=false}")
            state['mode'] = 'delayed'
            state['release'] = asyncio.Event()
            await page.locator('#submit-inquiry').click()
            for _ in range(50):
                if state['posts']: break
                await asyncio.sleep(0.02)
            assert len(state['posts']) == 1
            assert await page.locator('#submit-inquiry').is_disabled()
            await page.locator('#inquiry-form').evaluate("form => form.dispatchEvent(new Event('submit', {cancelable:true}))")
            assert len(state['posts']) == 1
            assert not await page.locator('#success-dialog').is_visible()
            sent = state['posts'][-1]
            for name in ['customer-name', 'move-date', 'date-undecided', 'message']:
                assert name not in sent, name
            assert sent['optional-consent'] == ['not-agreed']
            assert sent['required-consent'] == ['agreed']
            assert sent['overseas-consent'] == ['agreed']
            assert sent['consent-version'] == [fixture_config()['site']['policyVersion']]
            assert sent['inquiry-reference'][0].startswith('OK-')
            assert sent['subject'][0].startswith('[OK익스프레스] 새 이사 문의 · OK-')
            assert sent['phone'][0] not in sent['subject'][0]
            state['release'].set()
            await page.locator('#success-dialog').wait_for(state='visible')
            assert '이사 문의가 접수되었습니다. 내용을 확인한 뒤 연락드리겠습니다.' in await page.locator('#success-message').inner_text()
            await page.locator('#close-success').click()
            assert not await page.locator('#success-dialog').is_visible()
            assert await page.locator('#phone').input_value() == ''
            assert await page.locator('#submit-inquiry').evaluate('(element) => element === document.activeElement')
            results.append('모의 응답: 선택 동의 거부 시 값 제외, 중복 제출 차단, 응답 전 성공창 없음, 응답 후 성공 및 닫기')

            await fill_required()
            await page.locator('#optional-consent').check()
            await page.locator('#customer-name').fill('테스트 호칭')
            await page.locator('#date-undecided').check()
            await page.locator('#message').fill('계단 작업 여부 상담 테스트')
            for mode in ['network-failure', 'http-failure']:
                state['mode'] = mode
                before = len(state['posts'])
                await page.locator('#submit-inquiry').click()
                try:
                    await page.locator('#form-status').filter(has_text='접수 완료를 확인하지 못했습니다.').wait_for(timeout=5000)
                except Exception:
                    print('Failure diagnosis:', mode, 'posts', len(state['posts']), 'status', await page.locator('#form-status').inner_text(), 'errors', await page.locator('#error-summary').inner_text(), 'runtime', runtime_errors, 'form-state', await page.locator('#inquiry-form').evaluate('form => ({valid:form.checkValidity(),novalidate:form.noValidate,disabled:form.querySelector("button").disabled,fields:form.querySelector("fieldset").disabled,invalid:[...form.querySelectorAll(":invalid")].map(e=>e.id)})'))
                    raise
                assert len(state['posts']) == before + 1
                assert await page.locator('#phone').input_value() == '010-0000-0000'
                assert await page.locator('#customer-name').input_value() == '테스트 호칭'
                assert not await page.locator('#success-dialog').is_visible()
                assert not await page.locator('#submit-inquiry').is_disabled()
            assert state['posts'][-1]['inquiry-reference'] == state['posts'][-2]['inquiry-reference']
            state['mode'] = 'success'
            await page.locator('#submit-inquiry').click()
            await page.locator('#success-dialog').wait_for(state='visible')
            sent = state['posts'][-1]
            assert sent['customer-name'] == ['테스트 호칭']
            assert sent['date-undecided'] == ['undecided']
            assert 'move-date' not in sent
            await page.keyboard.press('Escape')
            assert not await page.locator('#success-dialog').is_visible()
            assert await page.evaluate('localStorage.length + sessionStorage.length') == 0
            assert urlsplit(page.url).query == ''
            assert not runtime_errors, runtime_errors
            results.append('모의 응답: 네트워크·HTTP 실패 시 값 유지 및 재시도, 선택 동의 전송, 미정 날짜, Escape 닫기, 저장소·URL에 개인정보 없음')

            await page.set_viewport_size({'width': 360, 'height': 800})
            await page.locator('#phone').focus()
            assert not await page.locator('.mobile-actions').is_visible()
            await page.locator('#phone').blur()
            await page.wait_for_timeout(20)
            assert await page.locator('.mobile-actions').is_visible()
            # Configured HTML still refuses receipts in a loopback preview.
            await page.goto('http://localhost:8000/')
            assert await page.locator('#inquiry-fields').evaluate('(element) => element.disabled')
            results.append('모바일 입력 포커스 중 고정 버튼 숨김, 로컬 미리보기에서 접수 잠금')

            await browser.close()
    report = {'checks': len(results), 'passed': results, 'live_netlify_submission': 'NOT RUN — no account access', 'live_email_delivery': 'NOT RUN — no mailbox access', 'official_sources': 'BLOCKED by environment egress proxy; not verified'}
    (artifacts / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
