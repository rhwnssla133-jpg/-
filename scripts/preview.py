#!/usr/bin/env python3
"""Create a portable, offline HTML preview; never enable online submissions."""
import base64
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def create_preview():
    dist = ROOT / 'dist'
    document = (dist / 'index.html').read_text(encoding='utf-8')
    if 'data-ready="false"' not in document:
        raise RuntimeError('The offline preview requires a locked inquiry form.')
    for filename in ['favicon.svg', 'moving-day.svg']:
        encoded = base64.b64encode((dist / 'assets' / filename).read_bytes()).decode()
        document = document.replace('/assets/' + filename, 'data:image/svg+xml;base64,' + encoded)
    css = (dist / 'assets/styles.css').read_text(encoding='utf-8')
    document = document.replace('<link rel="stylesheet" href="/assets/styles.css">', '<style>' + css + '\n[hidden]{display:none!important}</style>')
    document = document.replace('<main id="main">', '<main id="main" data-preview-page="home">', 1)
    pages = []
    for name in ['privacy', 'collection', 'compensation']:
        page = (dist / name / 'index.html').read_text(encoding='utf-8')
        body = re.search(r'<main\b.*?</main>', page, flags=re.S).group()
        body = body.replace('<main id="main">', f'<main id="{name}-page" data-preview-page="{name}" hidden>', 1)
        pages.append(body)
    document = document.replace('<footer class="site-footer">', ''.join(pages) + '<footer class="site-footer">', 1)
    # Keep all local page navigation within this one downloaded file.
    def link(match):
        path = match.group(1)
        if path.startswith('/#'):
            target = path[1:]
        else:
            parts = path.strip('/').split('/#')
            name = parts[0].rstrip('/')
            anchor = parts[1] if len(parts) > 1 else ''
            target = '#home' if not name else '#' + name + ('--' + anchor if anchor else '')
        return 'href="' + target + '"'
    document = re.sub(r'href="(/[^\"]*)"', link, document)
    document = document.replace(' target="_blank" rel="noopener"', '')
    app = (dist / 'assets/app.js').read_text(encoding='utf-8')
    router = '''
// Offline preview routing. All personal data collection remains disabled.
function showPreviewPage() {
  const hash = location.hash.slice(1);
  const [page, anchor] = hash.split('--');
  const name = ['privacy', 'collection', 'compensation'].includes(page) ? page : 'home';
  document.querySelectorAll('[data-preview-page]').forEach(node => {node.hidden = node.dataset.previewPage !== name;});
  if (name !== 'home') {
    const target = document.getElementById(anchor || name + '-page');
    target?.scrollIntoView();
  } else if (hash === 'home' || !hash) window.scrollTo(0,0);
  else document.getElementById(hash)?.scrollIntoView();
}
window.addEventListener('hashchange', showPreviewPage);
showPreviewPage();
'''
    document = document.replace('<script src="/assets/app.js" type="module"></script>', '<script type="module">' + app + router + '</script>')
    output = ROOT / 'artifacts/ok-express-preview.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(document, encoding='utf-8')
    print('Portable offline preview:', output)
    return output


if __name__ == '__main__':
    create_preview()
