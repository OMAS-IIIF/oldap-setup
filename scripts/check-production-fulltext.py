#!/usr/bin/env python3
"""Audit every source connector against explicit project field plans, offline.

The connector file is extracted from the frozen GraphDB filesystem snapshot;
connectors are not present in the RDF export. This compares names and paths only,
not GraphDB type/language/analyzer semantics. Projects without a connector are
recorded explicitly and never receive an invented index.
"""
import argparse
import hashlib
import json
from pathlib import Path


def audit(projects, connectors, plans):
    """Require complete project coverage and exact reviewed connector field paths.

    Args:
        projects: Project records with name and namespace from the RDF snapshot.
        connectors: GraphDB's saved connector-name to configuration mapping.
        plans: Portable YAML-derived plans, indexed by project short name.
    Returns:
        JSON-safe coverage and preserved source search restrictions for review.
    Raises:
        ValueError: Unknown/ambiguous project, missing plan or changed field paths.
    """
    names = {p['name'] for p in projects}
    if len(names) != len(projects) or not set(connectors) <= names or set(plans) != set(connectors):
        raise ValueError('Every connector needs an unambiguous project and explicit reviewed plan')
    result = []
    for project in sorted(projects, key=lambda p: p['name']):
        name = project['name']
        if name not in connectors:
            result.append({'project': name, 'status': 'no_source_index', 'fields': 0})
            continue
        config, plan = connectors[name], plans[name]
        fields = config.get('fields', [])
        paths = {f['fieldName']: f['propertyChain'] for f in fields}
        if not paths or len(paths) != len(fields) or config.get('detectFields'):
            raise ValueError('Dynamic, empty or duplicate source fields require review')
        if any(not f.get('indexed') or not f.get('analyzed') for f in fields):
            raise ValueError('Non-text source field requires explicit review')
        if plan['project'] != name or plan['graph'] != project['namespace']+'data' or plan['fields'] != paths:
            raise ValueError('Reviewed field map differs from the frozen source connector')
        result.append({'project': name, 'status': 'field_paths_match', 'fields': len(paths),
                       'configuration': {'graph': plan['graph'], 'fields': paths},
                       'source_types': config.get('types', []),
                       'source_languages': config.get('languages', []),
                       'semantic_parity_claimed': False})
    return {'status': 'passed', 'projects': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projects', type=Path, required=True)
    parser.add_argument('--connectors', type=Path, required=True)
    parser.add_argument('--plan', type=Path, action='append', required=True)
    args = parser.parse_args()
    plans = [json.loads(p.read_text()) for p in args.plan]
    if len({p['project'] for p in plans}) != len(plans):
        raise ValueError('Duplicate project plan')
    result = audit(json.loads(args.projects.read_text()), json.loads(args.connectors.read_text()),
                   {p['project']: p for p in plans})
    result['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [args.projects, args.connectors, *args.plan]}
    print(json.dumps(result, indent=2))
