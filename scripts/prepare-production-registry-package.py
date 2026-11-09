#!/usr/bin/env python3
"""Repackage a reviewed core using the same registry digests across Docker stores.

Classic Docker exposes config IDs; containerd may expose OCI manifest IDs. A bare
sha256 ID copied between these stores is therefore not a portable image selector.
Use the reviewed repository@digest without changing runtime bytes or credentials.
The original package remains untouched; a new manifest binds every changed file.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil

spec = importlib.util.spec_from_file_location('core_package', Path(__file__).with_name('prepare-production-package.py'))
core_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_package)


def repin(config, references):
    """Copy a Compose document and change only equivalent image selectors.

    The registry digest must equal the original reviewed manifest ID. Unknown
    images, mutable tags and mappings to a different digest fail closed.
    """
    result = copy.deepcopy(config)
    for service in result['services'].values():
        original = service['image']
        reference = references[original]
        if not re.fullmatch(r'[a-z0-9/_-]+@sha256:[a-f0-9]{64}', reference) or reference.split('@')[1] != original:
            raise ValueError('Registry reference must preserve the reviewed digest')
        service['image'] = reference
    return result


def build(source, plan_path, output):
    """Verify source bytes, then create a new immutable deployment package."""
    os.umask(0o077)
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError('Output must not modify the original package tree')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Source package must not contain links')
    original = json.loads((source/'manifest.json').read_text())
    actual = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if actual != set(original['files']) | {'manifest.json'}:
        raise ValueError('Source package contains unreviewed or missing files')
    for name, digest in original['files'].items():
        path = source/name
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Source package differs from its manifest')
    plan = json.loads(plan_path.read_text())['production_image_plan']
    references = {}
    for entry in plan:
        old = references.setdefault(entry['image_id'], entry['reference'])
        if old != entry['reference']:
            raise ValueError('Conflicting registry reference for reviewed image')
    configs = {role: repin(json.loads((source/role/'docker-compose.yml').read_text()), references)
               for role in ['api', 'media']}
    output.mkdir(mode=0o700)
    for role, config in configs.items():
        shutil.copytree(source/role, output/role)
        (output/role/'docker-compose.yml').write_text(json.dumps(config, indent=2)+'\n')
        core_package.archive(output/role, output/f'candidate-{role}.tar')
    shutil.copytree(source/'runtime', output/'runtime')
    shutil.copyfile(source/'candidate-runtime.tar', output/'candidate-runtime.tar')
    manifest = copy.deepcopy(original)
    manifest['images'] = {role:{name:s['image'] for name,s in doc['services'].items()} for role,doc in configs.items()}
    manifest['parent_manifest_sha256'] = hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()
    manifest['image_selection'] = 'reviewed registry digests; runtime and credentials unchanged'
    manifest['files'] = {str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'plan', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.plan, args.output)
    print('Prepared equivalent registry-pinned package; no deployment')
