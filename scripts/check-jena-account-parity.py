"""Read-only comparison of source users/projects/models with a local Jena API.

Run on the Docker host during rehearsal, and again after freezing source writers.
Credentials are read from the existing API process into memory, never arguments
or output. The sanitized report omits user IDs, tokens and response contents.
Any difference is reported; this command never repairs or approves permissions.
"""
import argparse
import json
import subprocess
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def normalized(value):
    """Ignore RDF multivalue order, preserving values and types exactly."""
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((normalized(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def run(source_container, target, graphdb):
    """Compare actual API representations without copying secrets to disk."""
    environment = json.loads(subprocess.check_output(['docker', 'exec', source_container, 'python', '-c',
        'import json,os; print(json.dumps({k:os.environ[k] for k in '
        '("OLDAP_AUTH_ADMIN_USER","OLDAP_AUTH_ADMIN_PASSWORD")}))']))
    container = json.loads(subprocess.check_output(['docker', 'inspect', source_container]))[0]
    addresses = [network['IPAddress'] for network in container['NetworkSettings']['Networks'].values()
                 if network['IPAddress']]
    if len(addresses) != 1:
        raise ValueError('Source must have exactly one unambiguous Docker network address')
    source = 'http://' + addresses[0] + ':8000'

    def read(base, path, token=None, body=None):
        request = Request(base + path, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json',
                                   **({'Authorization': 'Bearer ' + token} if token else {})})
        try:
            with urlopen(request, timeout=60) as response:
                return response.status, normalized(json.loads(response.read()))
        except HTTPError as error:
            return error.code, None  # Error bodies may contain private source values.

    def identifiers(predicate):
        query = ('SELECT ?id WHERE {GRAPH <http://oldap.org/base#admin> '
                 '{?s <http://oldap.org/base#' + predicate + '> ?id}} ORDER BY ?id')
        request = Request(graphdb, data=urlencode({'query': query, 'infer': 'false'}).encode(),
                          headers={'Accept': 'application/sparql-results+json'})
        with urlopen(request, timeout=60) as response:
            return [row['id']['value'] for row in json.loads(response.read())['results']['bindings']]

    report = {'scope': 'Read-only source/candidate comparison; not a cutover or consistency guarantee',
              'checks': [], 'differences': []}
    tokens = []
    for base in (source, target):
        status, body = read(base, '/admin/auth/' + quote(environment['OLDAP_AUTH_ADMIN_USER'], safe=''),
                            body={'password': environment['OLDAP_AUTH_ADMIN_PASSWORD']})
        if status != 200:
            raise ValueError(f'Administrator login failed: HTTP {status}')
        tokens.append(body['accessToken'])
        status, _ = read(base, '/admin/auth/unknown', body={})
        if status != 200:
            raise ValueError(f'Anonymous login failed: HTTP {status}')
    projects = identifiers('projectShortName')
    for kind, ids, prefix in [('users', identifiers('userId'), '/admin/user/'),
                              ('projects', projects, '/admin/project/'),
                              ('models', projects, '/admin/datamodel/')]:
        equal = 0
        for ordinal, identifier in enumerate(ids):
            path = prefix + quote(identifier, safe='')
            left = read(source, path, tokens[0])
            right = read(target, path, tokens[1])
            # Matching failures do not establish parity.
            if left[0] == right[0] == 200 and left[1] == right[1]:
                equal += 1
            else:
                fields = (sorted(key for key in left[1].keys() | right[1].keys()
                                 if left[1].get(key) != right[1].get(key))
                          if isinstance(left[1], dict) and isinstance(right[1], dict) else [])
                report['differences'].append({'kind': kind,
                    'item': ordinal if kind == 'users' else identifier,
                    'statuses': [left[0], right[0]], 'fields': fields})
        report['checks'].append({'kind': kind, 'total': len(ids), 'equal': equal})
    report['equal'] = not report['differences']
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-container', default='oldap-api')
    parser.add_argument('--target', default='http://127.0.0.1:18000')
    parser.add_argument('--graphdb', default='http://127.0.0.1:7200/repositories/oldap')
    args = parser.parse_args()
    result = run(args.source_container, args.target, args.graphdb)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['equal'] else 1)
