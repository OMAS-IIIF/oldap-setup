"""Build and publish isolated Jena release candidates without touching stable tags.

Prepare snapshots allowlisted package inputs (including uncommitted migration
work), builds wheels with exact private library versions, and records hashes.
Build loads and checks each architecture locally. Publish pushes those tested
image IDs, never rebuilds, refuses existing tags and records registry digests.
Registry tags are not an atomic lock: use one publisher per release bundle.
No PyPI upload or Git commit is performed. Stable tags require explicit --final
preparation; existing tags and latest are never replaced.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import certifi
import subprocess
import sys
import tomllib
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PYTHON_IMAGE = 'python@sha256:ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1'
PACKAGES = {'oldaplib': 'oldaplib', 'oldap-api': 'oldap_api', 'oldap-tools': 'src/oldap_tools'}
ARCHES = ('amd64', 'arm64')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def registry(reference):
    """Return public registry digest; only MANIFEST_UNKNOWN counts as absent."""
    repo, tag = reference.split(':', 1)
    context = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE') or certifi.where())
    query = urlencode({'service': 'registry.docker.io', 'scope': f'repository:{repo}:pull'})
    with urlopen('https://auth.docker.io/token?' + query, timeout=30, context=context) as response:
        token = json.load(response)['token']
    request = Request(f'https://registry-1.docker.io/v2/{repo}/manifests/{tag}', headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
    try:
        with urlopen(request, timeout=30, context=context) as response:
            return response.headers['Docker-Content-Digest']
    except HTTPError as error:
        body = json.loads(error.read())
        if error.code == 404 and any(e.get('code') == 'MANIFEST_UNKNOWN' for e in body.get('errors', [])):
            return None
        raise


def valid_reference(reference, final=False):
    """Only this workflow's repositories and content-qualified Jena RC tags."""
    if final:
        return bool(re.fullmatch(r'lrosenth/oldap-(?:api|tools):v\d+\.\d+\.\d+(?:-(?:amd64|arm64))?', reference))
    return bool(re.fullmatch(r'lrosenth/oldap-(?:api|tools):jena-\d+\.\d+\.\d+-rc[1-9]\d*-[a-f0-9]{12}(?:-(?:amd64|arm64))?', reference))


def candidate_tag(version, rc, fingerprint):
    """Map stable or rcN package metadata to the existing isolated image scheme.

    A prerelease's RC number must match the selected build, so an rc1 wheel
    cannot accidentally be advertised as an rc2 candidate.
    """
    match = re.fullmatch(r'(\d+\.\d+\.\d+)(?:rc([1-9]\d*))?', version)
    if not match or (match[2] is not None and int(match[2]) != rc):
        raise ValueError('Package version and selected candidate number differ')
    if rc < 1 or not re.fullmatch(r'[a-f0-9]{64}', fingerprint):
        raise ValueError('Invalid candidate number or source fingerprint')
    return f'jena-{match[1]}-rc{rc}-{fingerprint[:12]}'


def prepare(output, rc, final=False, constraints=None):
    """Create a new wheel bundle; original version files and Git stay unchanged."""
    if rc < 1:
        raise ValueError('RC number must be positive')
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for project, package in PACKAGES.items():
        source = ROOT.parent / project
        snapshot = output / 'sources' / project
        snapshot.mkdir(parents=True)
        selected = [source / 'pyproject.toml', source / 'README.md']
        selected += list(source.glob('LICENSE*'))
        for path in (source / package).rglob('*'):
            relative = path.relative_to(source)
            if any(p in ('test', 'tests', 'testdata', '__pycache__', 'standard') for p in relative.parts):
                continue
            if path.is_file() and (path.suffix in {'.py', '.json', '.yaml', '.trig', '.ttl'} or path.name == 'py.typed'):
                if path.is_symlink():
                    raise ValueError('Source symlinks are not accepted')
                selected.append(path)
        hashes = {}
        for path in sorted(selected):
            relative = path.relative_to(source)
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            hashes[str(relative)] = digest(target)
        metadata = tomllib.loads((snapshot / 'pyproject.toml').read_text())
        version = metadata.get('project', metadata.get('tool', {}).get('poetry', {}))['version']
        records[project] = {'commit': command('git', 'rev-parse', 'HEAD', cwd=source),
                            'dirty': bool(command('git', 'status', '--porcelain', cwd=source)),
                            'version': version, 'files': hashes}
    if final and any(record['dirty'] for record in records.values()):
        raise ValueError('Final release requires clean committed core sources')
    recipe_hash = digest(ROOT / 'release/Dockerfile.jena')
    fingerprint = hashlib.sha256(json.dumps({'sources': records, 'recipe': recipe_hash, 'builder': digest(Path(__file__)), 'python_image': PYTHON_IMAGE}, sort_keys=True).encode()).hexdigest()
    for record in records.values():
        candidate_tag(record['version'], rc, fingerprint)
    # Final wheels carry their actual public version, never a relabelled RC.
    if final and (len({r['version'] for r in records.values()}) != 1 or
                  any(not re.fullmatch(r'\d+\.\d+\.\d+', r['version']) for r in records.values())):
        raise ValueError('Final release requires matching stable core versions')
    suffix = '' if final else f'+jena.rc{rc}.{fingerprint[:12]}'
    lib_version = records['oldaplib']['version'] + suffix
    versions = {}
    for project in PACKAGES:
        snapshot = output / 'sources' / project
        version = records[project]['version'] + suffix
        versions[project] = version
        path = snapshot / 'pyproject.toml'
        text = re.sub(r'^version = "[^"]+"', f'version = "{version}"', path.read_text(), count=1, flags=re.M)
        if project != 'oldaplib':
            text = re.sub(r'^oldaplib = .+$', f'oldaplib = "=={lib_version}"', text, flags=re.M)
        path.write_text(text)
        for candidate in snapshot.rglob('*.py'):
            if candidate.name in ('version.py', '__init__.py'):
                text = candidate.read_text()
                text = re.sub(r'^__version__ = [^\n]+', f'__version__ = "{version}"', text, flags=re.M)
                candidate.write_text(text)
        wheels = output / 'wheels' / project
        wheels.mkdir(parents=True)
        subprocess.run([sys.executable, '-c', 'from poetry.core.masonry.api import build_wheel; import sys; build_wheel(sys.argv[1])', str(wheels)], cwd=snapshot, check=True)
    manifest = {'fingerprint': fingerprint, 'rc': rc, 'final': final, 'sources': records, 'versions': versions,
                'python_image': PYTHON_IMAGE, 'recipe_sha256': recipe_hash, 'components': {}}
    for project in ('oldap-api', 'oldap-tools'):
        tag = ('v' + records[project]['version']) if final else candidate_tag(records[project]['version'], rc, fingerprint)
        reference = f'lrosenth/{project}:{tag}'
        assert valid_reference(reference, final)
        context = output / project
        (context / 'wheels').mkdir(parents=True)
        for package in ('oldaplib', project):
            for wheel in (output / 'wheels' / package).glob('*.whl'):
                shutil.copyfile(wheel, context / 'wheels' / wheel.name)
        dockerfile = (ROOT / 'release/Dockerfile.jena').read_text()
        if constraints is not None:
            # Reuse the accepted installed dependency set when making a release.
            shutil.copyfile(constraints, context / 'constraints.txt')
            dockerfile = dockerfile.replace('RUN pip install --no-cache-dir /tmp/wheels/*.whl',
                'COPY constraints.txt /tmp/constraints.txt\nRUN pip install --no-cache-dir -c /tmp/constraints.txt /tmp/wheels/*.whl')
        if project == 'oldap-tools':
            # Preserve existing tools/root and API uid=100,gid=101 volume contracts.
            dockerfile = dockerfile.replace('USER app\n', '')
            dockerfile = dockerfile.replace('CMD ["gunicorn", "oldap_api.wsgi:app"]', 'ENTRYPOINT ["oldap-tools"]\nCMD ["--help"]')
        else:
            dockerfile += '\nHEALTHCHECK --interval=30s --timeout=10s --start-period=15s CMD python -c "from urllib.request import urlopen; urlopen(\'http://localhost:8000/status\', timeout=5)"\n'
        (context / 'Dockerfile').write_text(dockerfile)
        save(context / 'release.json', {'component': project, 'version': versions[project], 'library': lib_version,
                                        'source_fingerprint': fingerprint, 'sources': records})
        manifest['components'][project] = {'reference': reference,
            'context_sha256': {str(p.relative_to(context)): digest(p) for p in context.rglob('*') if p.is_file()}}
    save(output / 'release.json', manifest)
    print('Prepared', output, flush=True)


def verify(output):
    """Reject modified contexts and unsafe publication targets."""
    manifest = json.loads((output / 'release.json').read_text())
    if manifest.get('final', False):
        versions = manifest.get('versions', {})
        if set(versions) != set(PACKAGES) or len(set(versions.values())) != 1:
            raise ValueError('Final package versions must match')
        for project, version in versions.items():
            if not re.fullmatch(r'\d+\.\d+\.\d+', version) or manifest['sources'][project]['version'] != version:
                raise ValueError('Final metadata must contain exact stable versions')
        for project, info in manifest['components'].items():
            if info['reference'] != f'lrosenth/{project}:v{versions[project]}':
                raise ValueError('Final image tag must match its package version')
    for project, info in manifest['components'].items():
        if project not in ('oldap-api', 'oldap-tools') or not valid_reference(info['reference'], manifest.get('final', False)) or not info['reference'].startswith('lrosenth/' + project + ':'):
            raise ValueError('Unsafe image target')
        context = output / project
        actual = {str(p.relative_to(context)): digest(p) for p in context.rglob('*') if p.is_file()}
        if actual != info['context_sha256']:
            raise ValueError('Release context changed; prepare a new bundle')
    return manifest


def build(output):
    """Load and smoke-test both architectures locally; never push from a build."""
    manifest = verify(output)
    result = {}
    for project, info in manifest['components'].items():
        result[project] = {}
        for arch in ARCHES:
            reference = info['reference'] + '-' + arch
            subprocess.run(['docker', 'buildx', 'build', '--platform', 'linux/' + arch, '--load',
                            '--build-arg', 'PYTHON_IMAGE=' + manifest['python_image'],
                            '--label', 'org.opencontainers.image.revision=' + manifest['sources'][project]['commit'],
                            '--label', 'org.oldap.source.sha256=' + manifest['fingerprint'],
                            '--label', 'org.opencontainers.image.version=' + manifest['versions'][project],
                            '-t', reference, str(output / project)], check=True)
            image_id = command('docker', 'image', 'inspect', '--format', '{{.Id}}', reference)
            code = ('import importlib.metadata as m; from oldaplib.src.jena_connection import JenaConnection; '
                    f'assert m.version("oldaplib")=={manifest["versions"]["oldaplib"]!r}; '
                    f'assert m.version({project!r})=={manifest["versions"][project]!r}; '
                    'print("Verified installed migration packages")')
            subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/' + arch, '--entrypoint', 'python', image_id, '-c', code], check=True)
            subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/' + arch, '--entrypoint', 'python', image_id, '-m', 'pip', 'check'], check=True)
            if project == 'oldap-tools':
                subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/' + arch, image_id, '--help'], check=True, stdout=subprocess.DEVNULL)
            result[project][arch] = {'reference': reference, 'id': image_id}
    save(output / 'built.json', result)


def accept(output, release):
    """Exercise each packaged API architecture against the actual Jena service."""
    verify(output)
    built = json.loads((output / 'built.json').read_text())
    for project, images in built.items():
        expected = (100, 101) if project == 'oldap-api' else (0, 0)
        for arch, item in images.items():
            subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/' + arch,
                            '--entrypoint', 'python', item['id'], '-c',
                            f'import os; assert (os.getuid(), os.getgid()) == {expected!r}'], check=True)
    for arch in ARCHES:
        item = built['oldap-api'][arch]
        subprocess.run([sys.executable, str(ROOT / 'scripts/check-jena-network.py'),
                        '--release', str(release), '--api-image', item['id'], '--packaged'], check=True)
    save(output / 'accepted.json', built)


def publish(output):
    """Publish tested IDs under new RC tags only, then assemble a multiarch index."""
    manifest = verify(output)
    built = json.loads((output / 'built.json').read_text())
    acceptance = json.loads((output / 'accepted.json').read_text())
    if acceptance != built:
        raise ValueError('Integration acceptance does not match these image IDs')
    protected = [ref for p in manifest['components'] for ref in (f'lrosenth/{p}:latest', f'lrosenth/{p}:v' + manifest['sources'][p]['version'])]
    if manifest.get('final', False):
        protected = [ref for ref in protected if ref.endswith(':latest')]
    baseline = {ref: registry(ref) for ref in protected}
    save(output / 'protected-before.json', baseline)
    for project, info in manifest['components'].items():
        for reference in [info['reference'], *(built[project][a]['reference'] for a in ARCHES)]:
            if not valid_reference(reference, manifest.get('final', False)) or registry(reference) is not None:
                raise ValueError('Refusing existing/unsafe registry tag: ' + reference)
        for arch in ARCHES:
            item = built[project][arch]
            if item['reference'] != info['reference'] + '-' + arch:
                raise ValueError('Image reference mismatch')
            if command('docker', 'image', 'inspect', '--format', '{{.Id}}', item['reference']) != item['id']:
                raise ValueError('Local image tag changed after testing')
    published = {}
    for project, info in manifest['components'].items():
        refs = []
        for arch in ARCHES:
            item = built[project][arch]
            if registry(item['reference']) is not None:
                raise ValueError('Tag appeared before push; refusing overwrite')
            subprocess.run(['docker', 'push', item['reference']], check=True)
            remote_digest = registry(item['reference'])
            refs.append('lrosenth/' + project + '@' + remote_digest)
        if registry(info['reference']) is not None:
            raise ValueError('Index tag already exists')
        subprocess.run(['docker', 'buildx', 'imagetools', 'create', '-t', info['reference'], *refs], check=True)
        published[project] = {'reference': info['reference'], 'digest': registry(info['reference']), 'platform_manifests': refs}
        save(output / 'published.json', published)
    after = {ref: registry(ref) for ref in protected}
    save(output / 'protected-after.json', after)
    if baseline != after:
        raise RuntimeError('Latest changed during publication; inspect concurrent publisher activity')
    print(json.dumps(published, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'build', 'accept', 'publish'))
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--rc', type=int, default=1)
    parser.add_argument('--final', action='store_true', help='Prepare exact stable wheels and new vX.Y.Z tags')
    parser.add_argument('--constraints', type=Path, help='Accepted third-party pip constraints to retain in build contexts')
    parser.add_argument('--service-release', type=Path)
    args = parser.parse_args()
    output = args.bundle.resolve()
    if args.action == 'prepare':
        prepare(output, args.rc, args.final, args.constraints)
    elif args.action == 'accept':
        if args.service_release is None:
            parser.error('accept requires --service-release')
        accept(output, args.service_release.resolve())
    else:
        {'build': build, 'publish': publish}[args.action](output)
