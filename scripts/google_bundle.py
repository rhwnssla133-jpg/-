#!/usr/bin/env python3
"""Bundle the Google-hosted form and server into one pasteable Apps Script file."""
import json
from pathlib import Path
from build import ROOT, form_markup


def generate(config_path=None, output=None):
    c = json.loads(Path(config_path or ROOT / 'config.json').read_text(encoding='utf-8'))
    assets = ROOT / 'src/assets'
    origin = c['site']['url'].rstrip('/')
    form = form_markup(c, False).replace('href="/', 'href="' + origin + '/')
    validation = (assets / 'validation.js').read_text().replace('export function ', 'function ')
    client = (assets / 'google-form.js').read_text()
    css = (assets / 'styles.css').read_text()
    css += '\nbody{padding:8px 4px;background:#fff}dialog{position:fixed;top:20px;bottom:auto;margin:0 auto}body .mobile-actions{display:none}.form-help{font-size:11px}\n'
    dialog = '<dialog id="success-dialog" aria-labelledby="success-title" aria-describedby="success-message"><div class="success-icon" aria-hidden="true">✓</div><h2 id="success-title">문의가 접수되었습니다.</h2><p id="success-message">이사 문의가 접수되었습니다. 내용을 확인한 뒤 연락드리겠습니다.</p><p id="receipt-reference" class="receipt-reference"></p><button class="button button-orange" id="close-success" type="button">확인</button></dialog>'
    html = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>' + css + '</style></head><body><main><p id="availability-notice" class="availability-notice" role="status">문의창을 준비하고 있습니다.</p>' + form + '</main>' + dialog + '<script id="form-bootstrap" type="application/json">__FORM_BOOTSTRAP__</script><script>' + validation + client + '</script></body></html>'
    app = {key: c['business'][key] for key in ['name', 'phone', 'phoneLink']}
    app.update(origin=origin, policyVersion=c['site']['policyVersion'])
    server = (ROOT / 'google-apps-script/src/server.gs').read_text()
    # Insert the HTML last so placeholder-like customer/config strings cannot be reinterpreted.
    server = server.replace('__APP_CONFIGURATION__', json.dumps(app, ensure_ascii=False))
    server = server.replace('__GOOGLE_FORM_HTML__', json.dumps(html, ensure_ascii=False))
    target = Path(output or ROOT / 'google-apps-script/Code.gs')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(server, encoding='utf-8')
    return target


if __name__ == '__main__':
    print('Google Apps Script bundle:', generate())
