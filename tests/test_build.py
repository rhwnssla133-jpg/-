import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ok_build', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

def fixture_config():
    c = copy.deepcopy(json.loads((ROOT / 'config.json').read_text()))
    for key in ['representative', 'registrationNumber', 'address', 'transportPermit', 'openingHours', 'insuranceDetails']:
        c['business'][key] = '자동화 테스트 전용 값 (실제 사업정보 아님)'
    c['site'].update(url='https://ok-express-fixture.netlify.app', effectiveDate='2026-10-19')
    c['privacy'].update(responsiblePerson='테스트 담당자', department='테스트 부서', manualDeletionProcedureConfirmed=True, noticeReviewedOn='2026-10-19')
    g = c['integrations']['googleSheets']
    g.update(requested=True, deliveryConfigured=True, privacyReviewedOn='2026-10-19')
    for key, value in g['transfer'].items():
        g['transfer'][key] = ['테스트 전용'] if isinstance(value, list) else '테스트 전용 값'
    c['operation'].update(onlineRequested=True, contractAndCompensationReviewedOn='2026-10-19')
    return c

class BuildTests(unittest.TestCase):
    def test_default_is_locked_and_contains_no_netlify_form_or_iframe(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'site'; builder.build(ROOT / 'config.json', output)
            page = (output / 'index.html').read_text()
            self.assertIn('data-ready="false"', page)
            self.assertNotIn('data-netlify', page); self.assertNotIn('<iframe', page)
            self.assertNotIn('/.netlify/functions/', page)
            self.assertFalse((output / 'config.json').exists())
            for name in ['collection/index.html','privacy/index.html','compensation/index.html','_headers']:
                self.assertTrue((output / name).exists())
            builder.build(ROOT / 'config.json', output)

    def test_enabled_build_embeds_google_with_safe_csp_and_real_domain_seo(self):
        with tempfile.TemporaryDirectory() as d:
            c = fixture_config(); c['business']['representative'] = '<script>doNotRun()</script>'
            p = Path(d) / 'fixture.json'; p.write_text(json.dumps(c))
            out = Path(d) / 'site'; builder.build(p, out)
            page = (out / 'index.html').read_text()
            self.assertIn('id="google-inquiry"', page); self.assertIn('script.google.com/macros/s/', page)
            self.assertNotIn('data-netlify', page); self.assertNotIn('id="phone"', page)
            self.assertIn('&lt;script&gt;', page); self.assertIn('rel="canonical"', page)
            self.assertIn(c['site']['url'], (out / 'sitemap.xml').read_text())
            self.assertIn('frame-src https://script.google.com', (out / '_headers').read_text())
            privacy = (out / 'privacy/index.html').read_text()
            self.assertIn('Google 문의창', privacy)
            self.assertNotIn('문의 원본은 Netlify에 접수되고', privacy)

    def test_missing_google_privacy_and_business_keep_form_locked(self):
        c = fixture_config(); self.assertEqual(builder.readiness(c), [])
        for group, key in [('business','address'),('privacy','responsiblePerson'),('operation','onlineRequested')]:
            changed = copy.deepcopy(c); changed[group][key] = None
            self.assertIn(group + '.' + key, builder.readiness(changed))
        c['integrations']['googleSheets']['transfer']['countries'] = []
        self.assertIn('integrations.googleSheets.transfer.countries', builder.readiness(c))

    def test_unsafe_google_endpoint_rejected(self):
        for endpoint in ['http://script.google.com/macros/s/id/exec','https://example.com/exec','https://script.google.com/macros/s/id/exec?secret=value']:
            c = fixture_config(); c['integrations']['googleSheets']['webAppUrl'] = endpoint
            with self.assertRaises(ValueError): builder.readiness(c)

    def test_no_domain_is_invented(self):
        c = fixture_config(); c['site']['url'] = None
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fixture.json'; p.write_text(json.dumps(c)); out = Path(d) / 'site'
            builder.build(p, out)
            self.assertNotIn('rel="canonical"', (out / 'index.html').read_text())
            self.assertFalse((out / 'sitemap.xml').exists())

    def test_unknown_output_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): builder.build(ROOT / 'config.json', Path(d))

    def test_direct_thank_you_url_cannot_claim_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'site'; builder.build(ROOT / 'config.json', out)
            self.assertNotIn('이사 문의가 접수되었습니다.', (out / 'thank-you/index.html').read_text())

if __name__ == '__main__': unittest.main()
