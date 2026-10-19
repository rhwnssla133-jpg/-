"""Chromium validation. Google runtime/RPC is mocked; no real submissions or emails."""
import asyncio
import json
import mimetypes
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit, parse_qs
from playwright.async_api import async_playwright
from test_build import ROOT, builder, fixture_config
sys.path.insert(0, str(ROOT / 'scripts'))
from google_bundle import generate

async def main():
    results=[]; artifacts=ROOT/'artifacts'; artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ok-direct-google-') as temp:
        fixture=Path(temp)/'fixture.json'; config=fixture_config(); fixture.write_text(json.dumps(config))
        output=Path(temp)/'site'; builder.build(fixture,output)
        bundle=generate(fixture,Path(temp)/'Code.gs').read_text()
        # FORM_HTML is a JSON string literal, so decode it without executing server code.
        form_html=json.JSONDecoder().raw_decode(bundle.split('var FORM_HTML = ',1)[1])[0]
        base='https://ok-express-fixture.netlify.app'
        state={'enabled_site':False,'mode':'success','submissions':[],'release':None}
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
            context=await browser.new_context(viewport={'width':1440,'height':1000},locale='ko-KR',timezone_id='Asia/Seoul',reduced_motion='reduce')
            async def rpc(source,method,data):
                if method=='getFormConfiguration':
                    return {'enabled':True,'id':data or 'OK-00000000-0000-4000-8000-000000000001','sessionToken':'synthetic-session','policyVersion':config['site']['policyVersion']}
                assert method=='submitInquiry'
                state['submissions'].append(data)
                if state['mode']=='failure': raise RuntimeError('Synthetic provider failure')
                if state['mode']=='unconfirmed': return {'ok':False,'saved':False}
                if state['mode']=='delayed': await state['release'].wait()
                return {'ok':True,'saved':True,'emailSent':True,'id':data['id']}
            await context.expose_binding('mockGoogleCall',rpc)
            await context.add_init_script('''window.google={script:{get run(){let success, failure;const chain=new Proxy({}, {get(target,key){if(key==='withSuccessHandler')return f=>{success=f;return chain};if(key==='withFailureHandler')return f=>{failure=f;return chain};return data=>window.mockGoogleCall(key,data).then(value=>success(value)).catch(error=>failure(error));}});return chain;}}};''')
            async def route_handler(route):
                request=route.request; url=urlsplit(request.url)
                assert request.method=='GET', 'Customer data must use Google RPC, never URL/GET parameters'
                if url.hostname=='script.google.com':
                    channel=parse_qs(url.query)['channel'][0]
                    html='<html><body style="margin:0"><iframe title="Google runtime" style="width:100%;height:1900px;border:0" src="https://unit-script.googleusercontent.com/form?channel='+channel+'"></iframe></body></html>'
                    await route.fulfill(content_type='text/html',body=html); return
                if url.hostname=='unit-script.googleusercontent.com':
                    channel=parse_qs(url.query)['channel'][0]
                    html=form_html.replace('__FORM_BOOTSTRAP__',json.dumps({'origin':base,'channel':channel,'phoneLink':'tel:01025432424'}))
                    await route.fulfill(content_type='text/html',body=html); return
                root=output if state['enabled_site'] else ROOT/'dist'
                path=root/url.path.lstrip('/')
                if path.is_dir():path=path/'index.html'
                if not path.is_file():await route.fulfill(status=404,body='Not found');return
                await route.fulfill(content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',body=path.read_bytes())
            await context.route('**/*',route_handler)
            page=await context.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(base)
            assert await page.locator('#phone').is_disabled()
            assert await page.locator('input[type=checkbox]:checked').count()==0
            assert await page.locator('a[href^="tel:"]:not([href="tel:01025432424"])').count()==0
            await page.locator('.hero-actions a[href="#inquiry"]').click()
            assert urlsplit(page.url).fragment=='inquiry'
            results.append('전화 문의 기본값·동의 미선택·전화 링크·문의 이동')
            for width in [360,390,768,1024,1440]:
                await page.set_viewport_size({'width':width,'height':960});await page.evaluate('scrollTo(0,0)')
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                if width==360:
                    await page.screenshot(path=str(artifacts/'homepage-mobile.png'),full_page=True)
                    await page.locator('.menu-toggle').click();assert await page.locator('.menu-toggle').get_attribute('aria-expanded')=='true'
                    await page.keyboard.press('Escape');assert await page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
                if width==1440:await page.screenshot(path=str(artifacts/'homepage-desktop.png'),full_page=True)
            for path in ['/privacy/','/collection/','/compensation/']:
                await page.goto(base+path);await page.set_viewport_size({'width':360,'height':800})
                assert await page.locator('h1').is_visible();assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            results.append('360~1440px 배치·모바일 메뉴·개인정보·보상 페이지')
            state['enabled_site']=True;await page.goto(base)
            frame=page.frame_locator('#google-inquiry').frame_locator('iframe')
            await frame.locator('#phone').wait_for()
            assert not await frame.locator('#phone').is_disabled()
            assert await page.locator('#google-inquiry').is_visible()
            for width in [360,390,768,1440]:
                await page.set_viewport_size({'width':width,'height':900})
                assert await frame.locator('html').evaluate('e=>e.scrollWidth<=innerWidth'),width
            await page.set_viewport_size({'width':390,'height':844})
            await frame.locator('#submit-inquiry').click()
            assert await frame.locator('#error-summary li').count()==6
            await frame.locator('#error-summary a').first.click()
            assert await frame.locator('#phone').evaluate('e=>e===document.activeElement')
            async def required():
                await frame.locator('#phone').fill('010-0000-0000');await frame.locator('#move-type').select_option('포장이사')
                await frame.locator('#origin-area').fill('광주 북구 용봉동');await frame.locator('#destination-area').fill('광주 광산구 수완동')
                await frame.locator('#required-consent').check();await frame.locator('#overseas-consent').check()
            await required();await frame.locator('#phone').fill('123');await frame.locator('#submit-inquiry').click()
            assert '전화번호 형식' in await frame.locator('#phone-error').inner_text()
            await required();await frame.locator('#optional-consent').check();await frame.locator('#move-date').fill('2020-01-01')
            await frame.locator('#submit-inquiry').click();assert '오늘 이후' in await frame.locator('#move-date-error').inner_text()
            results.append('Google iframe·중첩 Google 호스트 통신·모바일 폼 배치·필수값/전화/날짜 오류')
            await frame.locator('#customer-name').fill('테스트 호칭');await frame.locator('#message').fill('동의 해제 테스트')
            await frame.locator('#optional-consent').uncheck()
            assert await frame.locator('#customer-name').input_value()==''
            assert await frame.locator('#message').is_disabled()
            state['mode']='delayed';state['release']=asyncio.Event()
            await frame.locator('#submit-inquiry').click()
            for _ in range(100):
                if state['submissions']:break
                await asyncio.sleep(.02)
            assert len(state['submissions'])==1
            assert await frame.locator('#submit-inquiry').is_disabled()
            await frame.locator('form').evaluate("f=>f.dispatchEvent(new Event('submit',{cancelable:true}))")
            assert len(state['submissions'])==1
            assert not await frame.locator('#success-dialog').is_visible()
            data=state['submissions'][-1]
            for key in ['customer-name','move-date','date-undecided','message']:assert key not in data,key
            assert data['optional-consent']=='not-agreed'
            state['release'].set();await frame.locator('#success-dialog').wait_for(state='visible')
            await frame.locator('#close-success').click();await frame.locator('#success-dialog').wait_for(state='hidden')
            assert await frame.locator('#phone').input_value()==''
            results.append('모의 Google RPC: 저장 전 성공 미표시·중복 클릭 방지·선택정보 제외·성공창 닫기')
            await required();await frame.locator('#optional-consent').check();await frame.locator('#message').fill('계단 작업 상담 테스트')
            for mode in ['failure','unconfirmed']:
                state['mode']=mode;await frame.locator('#submit-inquiry').click()
                await frame.locator('#form-status').filter(has_text='접수 완료를 확인하지 못했습니다.').wait_for()
                assert await frame.locator('#phone').input_value()=='010-0000-0000'
                assert await frame.locator('#message').input_value()=='계단 작업 상담 테스트'
                assert not await frame.locator('#success-dialog').is_visible()
            assert state['submissions'][-1]['id']==state['submissions'][-2]['id']
            state['mode']='success';await frame.locator('#submit-inquiry').click();await frame.locator('#success-dialog').wait_for(state='visible')
            await frame.locator('#close-success').click()
            assert await page.evaluate('localStorage.length+sessionStorage.length')==0
            storage = await frame.locator('html').evaluate('()=>{try{return localStorage.length+sessionStorage.length}catch(e){if(e.name==="SecurityError")return "blocked";throw e}}')
            assert storage in [0, 'blocked']
            assert urlsplit(page.url).query==''
            assert not errors,errors
            results.append('모의 Google RPC: 실패·저장 미확인 시 입력 유지·동일 참조 재시도·URL/저장소에 개인정보 없음')
            await page.evaluate('scrollTo(0,document.getElementById("inquiry").offsetTop)')
            await page.screenshot(path=str(artifacts/'google-form-mobile.png'))
            await browser.close()
    report={'checks':len(results),'passed':results,'live_google_sheet':'NOT RUN — Google account deployment required','live_gmail_delivery':'NOT RUN — mailbox access unavailable','google_runtime':'MOCKED — iframe and google.script.run contract validated'}
    (artifacts/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
