#!/usr/bin/env python3
"""Build upload-ready ZIP and editable source ZIP, without Git data or test artifacts."""
from pathlib import Path
import shutil
import zipfile
from build import ROOT, build

build(ROOT / 'config.json', ROOT / 'dist')
artifacts = ROOT / 'artifacts'
artifacts.mkdir(exist_ok=True)
with zipfile.ZipFile(artifacts / 'ok-express-netlify.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((ROOT / 'dist').rglob('*')):
        if path.is_file() and path.name != '.ok-express-build':
            archive.write(path, path.relative_to(ROOT / 'dist'))
shutil.copyfile(artifacts / 'ok-express-netlify.zip', ROOT / 'ok-express-netlify.zip')
with zipfile.ZipFile(artifacts / 'ok-express-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    roots = ['src', 'scripts', 'tests', 'docs', 'netlify', 'google-apps-script', 'templates', 'config.json', 'netlify.toml', 'README.md', 'requirements-dev.txt', '.gitignore']
    for name in roots:
        root = ROOT / name
        paths = sorted(root.rglob('*')) if root.is_dir() else [root]
        for path in paths:
            if path.is_file() and '__pycache__' not in path.parts:
                archive.write(path, path.relative_to(ROOT))
print('ZIPs: artifacts/ok-express-netlify.zip, artifacts/ok-express-source.zip')
