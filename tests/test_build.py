import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ok_build', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fixture_config():
    """Synthetic configuration, for mocked browser tests only. Never deployed."""
    c = copy.deepcopy(json.loads((ROOT / 'config.json').read_text()))
    for key in ['representative', 'registrationNumber', 'address', 'transportPermit', 'openingHours', 'insuranceDetails']:
        c['business'][key] = '자동화 테스트 전용 값 (실제 사업정보 아님)'
    c['site'].update(url='https://ok-express-fixture.netlify.app', effectiveDate='2026-10-19')
    c['privacy'].update(responsiblePerson='테스트 담당자', department='테스트 부서', manualDeletionProcedureConfirmed=True, noticeReviewedOn='2026-10-19')
    for key, value in c['privacy']['transfer'].items():
        if not value:
            c['privacy']['transfer'][key] = ['테스트 전용'] if isinstance(value, list) else '자동화 테스트 전용'
    c['operation'].update(onlineRequested=True, netlifyFormsConfigured=True, emailNotificationConfigured=True, contractAndCompensationReviewedOn='2026-10-19')
    return c


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.json').read_text())

    def test_default_is_locked_and_no_domain_is_invented(self):
        self.assertGreater(len(builder.readiness(self.config)), 20)
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'site'
            builder.build(ROOT / 'config.json', output)
            page = (output / 'index.html').read_text()
            self.assertIn('data-ready="false"', page)
            self.assertIn('data-netlify="true"', page)
            self.assertIn('name="form-name" value="ok-express-inquiry"', page)
            self.assertNotIn('rel="canonical"', page)
            self.assertFalse((output / 'sitemap.xml').exists())
            self.assertFalse((output / 'config.json').exists())
            self.assertNotIn('이사 문의가 접수되었습니다.', (output / 'thank-you/index.html').read_text())
            for filename in ['privacy/index.html', 'collection/index.html', 'compensation/index.html', '_headers', '404.html']:
                self.assertTrue((output / filename).exists(), filename)
            # Rebuild in place to exercise safe, repeatable refresh.
            builder.build(ROOT / 'config.json', output)

    def test_no_single_switch_can_enable_incomplete_configuration(self):
        self.config['operation']['onlineRequested'] = True
        self.assertTrue(builder.readiness(self.config))

    def test_each_required_setting_blocks_inquiry(self):
        configured = fixture_config()
        self.assertEqual(builder.readiness(configured), [])
        for group, keys in [('business', ['representative', 'registrationNumber', 'address', 'transportPermit']), ('operation', ['netlifyFormsConfigured', 'emailNotificationConfigured']), ('privacy', ['manualDeletionProcedureConfirmed', 'noticeReviewedOn'])]:
            for key in keys:
                changed = copy.deepcopy(configured)
                changed[group][key] = None
                self.assertIn(f'{group}.{key}', builder.readiness(changed))
        changed = copy.deepcopy(configured)
        changed['privacy']['transfer']['countries'] = []
        self.assertIn('privacy.transfer.countries', builder.readiness(changed))

    def test_configured_domain_generates_seo_and_html_is_escaped(self):
        c = fixture_config()
        c['business']['representative'] = '<script>doNotRun()</script>'
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / 'fixture.json'
            config.write_text(json.dumps(c))
            output = Path(d) / 'site'
            builder.build(config, output)
            page = (output / 'index.html').read_text()
            self.assertIn('data-ready="true"', page)
            self.assertIn('rel="canonical"', page)
            self.assertIn('property="og:url"', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('<script>doNotRun()', page)
            self.assertIn(c['site']['url'], (output / 'sitemap.xml').read_text())

    def test_refuse_unknown_output_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                builder.build(ROOT / 'config.json', Path(d))

    def test_google_integration_requires_separate_privacy_confirmation(self):
        c = fixture_config()
        c['integrations']['googleSheets']['requested'] = True
        missing = builder.readiness(c)
        self.assertIn('integrations.googleSheets.deliveryConfigured', missing)
        self.assertIn('integrations.googleSheets.transfer.countries', missing)
        self.assertNotIn('operation.emailNotificationConfigured', missing)

    def test_refuse_insecure_domain(self):
        for bad in ['http://example.com', 'https://user:password@example.com', 'https://example.com/path', 'https://example.com/?query=1']:
            self.config['site']['url'] = bad
            with self.assertRaises(ValueError):
                builder.readiness(self.config)


if __name__ == '__main__':
    unittest.main()
