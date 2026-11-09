#!/usr/bin/env python3
"""Prepare isolated Jena storage from an accepted, still-frozen source checkpoint.

Never replace Compose configuration or start application services here. Verify the
retained package hashes, convert only fresh checkpoint RDF, apply the reviewed
operators, audit all source text indexes and verify a persisted new TDB import.
Failure leaves the new directory for inspection, never overwrites/reuses it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import subprocess
import tarfile

JAVA_IMAGE = 'eclipse-temurin@sha256:ecdc0adb37bde1a281c4d245a3cd535004b1fc8322d560f5b09463b248c81df0'
TARGET = Path('/srv/storage/oldap-jena-production-20261108')
PACKAGE = Path('/srv/storage/oldap-release-candidate-20261108')
EXPECTED = {
    'candidate-runtime.tar': '77a451e03de0261345057b637ca963431308ed9984dd90ad7925e9a8b6c4f860',
    'candidate-migration.tar': 'e0967af0347af4a0353207d487ceeb18e771afbabfe873051457fef5a37a4b0f',
}


def digest(path):
    """Hash an ordinary immutable input without following a final symlink."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected ordinary input file')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_archive(path, expected):
    """Require the reviewed bytes and ordinary relative members before extraction."""
    if digest(path) != expected:
        raise ValueError('Release archive checksum mismatch')
    with tarfile.open(path) as archive:
        seen = set()
        for item in archive.getmembers():
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or str(name) in seen or not (item.isfile() or item.isdir()):
                raise ValueError('Unsafe or duplicate release member')
            if item.mode & 0o7022:
                raise ValueError('Unsafe release member permissions')
            seen.add(str(name))


def prepare(snapshot_id):
    """Return evidence for a new offline target; source files remain untouched."""
    if not re.fullmatch('[a-zA-Z0-9_-]+', snapshot_id):
        raise ValueError('Invalid checkpoint ID')
    checkpoint = Path('/srv/storage') / ('oldap-cutover-' + snapshot_id)
    if checkpoint.is_symlink() or checkpoint.stat().st_uid != 0 or checkpoint.stat().st_mode & 0o777 != 0o700:
        raise ValueError('Require private root-owned source checkpoint')
    manifest = json.loads((checkpoint / 'manifest.json').read_text())
    if manifest['status'] != 'source-frozen' or manifest['snapshot_id'] != snapshot_id:
        raise ValueError('Require completed held source')
    if subprocess.check_output(['docker', 'ps', '-q'], text=True).strip():
        raise ValueError('Keep original API-host services stopped during preparation')
    if TARGET.exists() or TARGET.is_symlink():
        raise FileExistsError('Target must be new; inspect failed attempts separately')
    source_rdf = checkpoint / 'source.trig'
    source_hash = digest(source_rdf)
    if not any(item['path'] == str(source_rdf) and item['checksum'] == source_hash for item in manifest['artifacts']):
        raise ValueError('Fresh RDF differs from frozen manifest')
    for name, expected in EXPECTED.items():
        validate_archive(PACKAGE / name, expected)
    TARGET.mkdir(mode=0o700)
    os.chown(TARGET, 1000, 1000)
    migration = TARGET / 'migration'
    migration.mkdir(mode=0o700)
    for name, destination in [('candidate-runtime.tar', TARGET), ('candidate-migration.tar', migration)]:
        subprocess.run(['tar', '-xf', str(PACKAGE / name), '-C', str(destination)], check=True)
    data = TARGET / 'data'
    data.mkdir(mode=0o755)
    (data / 'native').mkdir(mode=0o700)
    for source, target in [('/srv/storage/oldap-data/oldap-api', data / 'api'),
                           ('/opt/oldap/compose/redis-data', data / 'redis')]:
        source = Path(source)
        if source.is_symlink() or not source.is_dir() or any(p.is_symlink() for p in source.rglob('*')):
            raise ValueError('Unexpected operational-state symlink or missing source')
        subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(target)], check=True)
    evidence = TARGET / 'migration-evidence'
    evidence.mkdir(mode=0o700)
    base = ['docker', 'run', '--rm', '--network', 'none', '--memory', '2g', '--cpus', '2',
            '--mount', f'type=bind,src={TARGET},dst=/target',
            '--mount', f'type=bind,src={source_rdf},dst=/input/source.trig,readonly',
            JAVA_IMAGE, 'java', '-Xmx1g', '-cp', '/target/migration/classes:/target/release/lib/*']
    def java(name, *args):
        subprocess.run(base + [name, *args], check=True)
    def inside(path):
        return '/target/' + str(path.relative_to(TARGET))
    converted = evidence / 'converted'
    java('ConvertLegacyRdfStar', '/input/source.trig', inside(converted))
    reviewed = evidence / 'reviewed'
    java('PrepareReviewedProductionRdf', inside(converted / 'converted.trig'), digest(converted / 'converted.trig'),
         inside(migration / 'home-writer-recovery-default.ru'), inside(migration / 'fasnacht-parts-preflight.rq'),
         inside(migration / 'fasnacht-parts.ru'), inside(reviewed))
    inventory = evidence / 'inventory'
    java('InventoryProductionModel', inside(reviewed / 'reviewed.trig'), digest(reviewed / 'reviewed.trig'), inside(inventory))
    # Inventory every filesystem connector from the stopped source, not only RDF.
    connectors = list(Path('/srv/storage/graphdb').rglob('lucene-connector/config.json'))
    if len(connectors) != 1:
        raise ValueError('Unexpected source connector layout; review all indexes')
    connector_copy = evidence / 'source-connectors.json'
    connector_copy.write_bytes(connectors[0].read_bytes())
    output = subprocess.check_output(['python3', str(migration / 'check-production-fulltext.py'),
        '--projects', str(inventory / 'projects.json'), '--connectors', str(connector_copy),
        '--plan', str(migration / 'fasnacht-fulltext-plan.json')])
    (evidence / 'fulltext-audit.json').write_bytes(output)
    model = evidence / 'model'
    java('PrepareProductionModel', inside(reviewed / 'reviewed.trig'), digest(reviewed / 'reviewed.trig'), inside(model))
    cleaned = model / 'model-reviewed.trig'
    java('JenaInitialImport', inside(cleaned), digest(cleaned), '/target/data/native/dataset')
    subprocess.run(['chown', '-R', '1000:1000', str(data / 'native')], check=True)
    (TARGET / 'config/service.properties').chmod(0o600)
    os.chown(TARGET / 'config/service.properties', 1000, 1000)
    report = {'status': 'offline-import-passed', 'snapshot_id': snapshot_id,
              'source_sha256': source_hash, 'target_rdf_sha256': digest(cleaned),
              'target_root': str(TARGET), 'source_unchanged': True,
              'public_services_started': False, 'redis_cache_cleanup_pending': True}
    (evidence / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot_id')
    args = parser.parse_args()
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'dhlab-oldap':
        parser.error('Run as root on the frozen production API VM')
    os.umask(0o077)
    print(json.dumps(prepare(args.snapshot_id), indent=2))
