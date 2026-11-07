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
        inspected = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag]))[0]
        if inspected['RootFS']['Layers'] != config['rootfs']['diff_ids']:
            raise ValueError('Loaded filesystem layers differ')
        # Read the complete export stream; verify the raw config, not the engine's
        # displayed image ID (legacy config digest versus containerd manifest ID).
        process = subprocess.Popen(['docker', 'image', 'save', tag], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        found = False
        with tarfile.open(fileobj=process.stdout, mode='r|') as exported:
            for member in exported:
                if member.isfile() and Path(member.name).name.removesuffix('.json') == digest:
                    if hashlib.sha256(exported.extractfile(member).read()).hexdigest() != digest:
                        raise ValueError('Re-exported config checksum mismatch')
                    found = True
        process.stdout.read()
        if process.wait() != 0 or not found:
            raise RuntimeError('Re-export verification failed')
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
