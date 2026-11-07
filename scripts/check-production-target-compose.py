#!/usr/bin/env python3
"""Read the selected production target privately before starting any consumer.

Requires pinned target images, Jena API wiring and new API/Redis writable paths.
Source database/coordinator data must remain untouched for pre-opening rollback.
This is a configuration guard, not a replacement for private application acceptance.
"""
import json
from pathlib import Path
import re
import subprocess
import sys


def validate(role, config, root):
    """Reject mutable images or source-state mounts in the private target."""
    services = config['services']
    required = (['oldap-jena','oldap-jena-identity','oldap-api','redis','caddy','oldap-app','fasnachts-page','salsah-2']
                if role == 'api' else ['mediaserver','imageserver','ingest-worker','export-worker','mobile-media-worker','caddy'])
    for name in required:
        image = services[name]['image']
        if not re.fullmatch(r'(?:[^\s]+@)?sha256:[a-f0-9]{64}', image):
            raise ValueError('Every target image must be pinned: '+name)
    if role == 'api':
        if services['oldap-api']['environment'].get('OLDAP_BACKEND') != 'jena':
            raise ValueError('API must select Jena')
        data_root = (root/'data').resolve()
        for name in ['oldap-api','redis','oldap-jena']:
            writable = []
            for mount in services[name].get('volumes', []):
                if mount.get('read_only'):
                    continue
                source = Path(mount.get('source','/')).resolve()
                writable.append(source)
                if mount.get('type') != 'bind' or not source.is_relative_to(data_root) or source == data_root:
                    raise ValueError('Target writable state must be strictly below new candidate data root')
            if not writable:
                raise ValueError('Target persistent storage is missing: '+name)
        for name in ['oldap-api', 'oldap-jena-identity']:
            if services[name].get('network_mode') != 'service:oldap-jena':
                raise ValueError('API and identity must share the native namespace')
        if services['oldap-jena'].get('ports'):
            raise ValueError('Native backend must not publish ports')


if __name__ == '__main__':
    config = json.loads(subprocess.check_output(['docker','compose','--profile','*','config','--format','json'],
                                               cwd=sys.argv[2], stderr=subprocess.PIPE))
    validate(sys.argv[1], config, Path(sys.argv[3]))
