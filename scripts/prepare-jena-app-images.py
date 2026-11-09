#!/usr/bin/env python3
"""Freeze reviewed app sources into secret-free, hash-addressed build contexts.

Does not publish or deploy. Build the emitted contexts using the recorded recipe;
record image digests before activation. Uncommitted source fixes are included.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

workspace = Path(__file__).resolve().parents[2]
destination = Path(sys.argv[1]).expanduser().resolve()
destination.mkdir(parents=True, exist_ok=False)
components = {}
for name, repository, version in [('oldap-app', 'oldap-app', '0.2.7'),
                                  ('salsah-2', 'salsah-2', '0.0.2'),
                                  ('FasnachtsPage', 'fasnachts-page', '0.1.49'),
                                  ('oldap-mediaserver', 'oldap-mediahelper', '0.2.17')]:
    source = workspace / name
    media = name == 'oldap-mediaserver'
    if not media:
        # Frontend tags follow the source package version, including final releases.
        version = json.loads((source / 'package.json').read_text())['version']
    directories = {'mediaserver'} if media else {'src', 'static', 'messages', 'project.inlang', 'scripts'}
    roots = ({'pyproject.toml', 'poetry.lock', 'README.md'} if media else
             {'package.json', 'package-lock.json', 'Dockerfile', '.dockerignore', 'docker-entrypoint.sh',
              'svelte.config.js', 'vite.config.ts', 'tsconfig.json', 'vitest-setup-client.ts'})
    context = destination / name
    context.mkdir()
    files = subprocess.check_output(['git', '-C', str(source), 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).decode().split('\0')
    hashes = {}
    for rel in sorted(set(files) - {''}):
        path = Path(rel)
        if path.parts[0] not in directories and rel not in roots:
            continue
        if any(part.startswith('.env') or part in {'__pycache__', 'node_modules'} for part in path.parts):
            continue
        original = source / rel
        if original.is_symlink():
            raise ValueError(f'Symlink requires review: {original}')
        if not original.is_file():
            continue
        target = context / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        hashes[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    components[name] = {'repository': 'lrosenth/' + repository, 'version': version,
                        'tag': f'jena-{version}-rc1-{fingerprint[:12]}-amd64',
                        'source_commit': subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
                        'fingerprint': fingerprint, 'files': hashes,
                        'dockerfile': 'mediaserver/Dockerfile' if media else 'Dockerfile'}
(destination / 'sources.json').write_text(json.dumps(components, indent=2) + '\n')
print(json.dumps({key: value['tag'] for key, value in components.items()}, indent=2))
