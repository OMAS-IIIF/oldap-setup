#!/usr/bin/env python3
"""Verify legacy Docker archives through a separate Docker Desktop engine.

Some legacy exports contain all images in manifest.json but only one OCI index
entry. Preserve the original; create an explicitly tagged Docker-format import
copy (without the misleading OCI index), load it, and re-export each tag to
verify its original config SHA and layer identities. Tags use a dedicated local
namespace; no source or published tags are changed, and no container is started.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile


def verify_loaded_image(tag, digest, expected_layers=None):
    """Verify loaded bytes across engines with different displayed image IDs.

    Re-export the selected image and check its original config hash and layer
    identities. Return the current engine's immutable ID for Compose pinning.
    The private compatibility tag is only a lookup hint, never proof of identity.
    """
    inspected = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], stderr=subprocess.PIPE))[0]
    process = subprocess.Popen(['docker', 'image', 'save', tag], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    config = None
    with tarfile.open(fileobj=process.stdout, mode='r|') as exported:
        for member in exported:
            if member.isfile() and Path(member.name).name.removesuffix('.json') == digest:
                raw = exported.extractfile(member).read()
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError('Re-exported config checksum mismatch')
                config = json.loads(raw)
    process.stdout.read()
    if process.wait() != 0 or config is None:
        raise RuntimeError('Re-export verification failed')
    layers = config['rootfs']['diff_ids']
    if inspected['RootFS']['Layers'] != layers or (expected_layers is not None and expected_layers != layers):
        raise ValueError('Loaded filesystem layers differ')
    return inspected['Id']


def resolve_source_image(source_id, role):
    """Use an exact OCI/config identity, or verify a legacy compatibility import.

    Newer source engines record OCI index IDs; loading their complete original
    archives preserves that identity. Legacy config IDs may instead require the
    private compatibility tag and a byte-verified re-export on the target engine.
    """
    result = subprocess.run(['docker', 'image', 'inspect', source_id], capture_output=True, text=True)
    if result.returncode == 0:
        installed = json.loads(result.stdout)[0]
        if installed['Id'] == source_id:
            return source_id
    digest = source_id.removeprefix('sha256:')
    return verify_loaded_image('oldap-rollback/'+role+':'+digest, digest)


def verify(source, target, prefix):
    """Create a fresh compatibility archive and verify all loaded image contents."""
    os.umask(0o077)
    if target.exists():
        raise ValueError('Compatibility output must be new')
    configs = {}
    with tarfile.open(source) as archive:
        manifests = json.load(archive.extractfile('manifest.json'))
        for item in manifests:
            data = archive.extractfile(item['Config']).read()
            digest = hashlib.sha256(data).hexdigest()
            if Path(item['Config']).name.removesuffix('.json') != digest:
                raise ValueError('Config checksum mismatch')
            tag = 'oldap-rollback/'+prefix+':'+digest
            configs[tag] = (digest, json.loads(data))
            item['RepoTags'] = [tag]
        with tarfile.open(target, 'w') as copy:
            for member in archive:
                if member.name in {'index.json', 'oci-layout', 'manifest.json'}:
                    continue
                copy.addfile(member, archive.extractfile(member) if member.isfile() else None)
            data = json.dumps(manifests).encode()
            header = tarfile.TarInfo('manifest.json')
            header.size = len(data)
            copy.addfile(header, io.BytesIO(data))
    target.chmod(0o600)
    subprocess.run(['docker', 'image', 'load', '-i', str(target)], capture_output=True, check=True)
    for tag, (digest, config) in configs.items():
        verify_loaded_image(tag, digest, config['rootfs']['diff_ids'])
    with target.open('rb') as stream:
        target_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'original': source.name, 'compatibility_archive': target.name,
              'compatibility_sha256': target_hash, 'image_config_ids': [v[0] for v in configs.values()],
              'load_and_reexport_verified': True}
    target.with_suffix('.verified.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'archive': source.name, 'verified_images': len(configs)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('prefix', choices=['api', 'batch', 'media'])
    args = parser.parse_args()
    verify(args.source, args.target, args.prefix)
