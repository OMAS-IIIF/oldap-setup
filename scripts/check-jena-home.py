"""Check the public home cutover without printing credentials or media tokens.

Run on api.home.org after activation. Reads real public/admin APIs and one known
public image; does not change source or target RDF. The optional story digest is
the normalized response recorded from the final source rehearsal.
"""
import argparse
import hashlib
import json
import subprocess
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def normalized(value):
    """Ignore RDF result ordering while preserving every scalar value."""
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((normalized(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def normalized_stories(rows):
    """Compare the known keyword IRI aliases without changing literal text.

    Workers may compact this registered list namespace differently. Only the
    IRI-valued storyKeywords property is expanded; titles and other values stay
    exact. This is an acceptance comparison, not an API serialization change.
    """
    expanded = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get('fasnacht:storyKeywords'), list):
            item['fasnacht:storyKeywords'] = [
                'http://fasnacht.digital/ns/StoryKeywords#' + value[len('L-StoryKeywords:'):]
                if isinstance(value, str) and value.startswith('L-StoryKeywords:') else value
                for value in item['fasnacht:storyKeywords']
            ]
        expanded.append(item)
    return normalized(expanded)


def run(expected_stories, expected_semantic_stories=None):
    """Return sanitized checks; stop on failed readiness, isolation or delivery."""
    report = {'checks': []}

    def check(label, condition):
        if not condition:
            raise RuntimeError('Failed acceptance: ' + label)
        report['checks'].append(label)

    def request(url, body=None, token=None):
        request = Request(url, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json',
                                   **({'Authorization': 'Bearer ' + token} if token else {})})
        try:
            with urlopen(request, timeout=60) as response:
                return response.status, response.read()
        except HTTPError as error:
            # Never put signed URLs or response bodies into exception/report text.
            return error.code, error.read()

    def api(path, body=None, token=None):
        status, content = request('http://api.home.org' + path, body, token)
        check('API ' + path.split('?')[0] + ' HTTP 200', status == 200)
        return json.loads(content)

    containers = json.loads(subprocess.check_output(['docker', 'inspect',
        'oldap-api', 'compose-oldap-jena-1', 'compose-oldap-jena-identity-1', 'graphdb', 'redis', 'caddy']))
    state = {item['Name'].lstrip('/'): item for item in containers}
    env = dict(item.split('=', 1) for item in state['oldap-api']['Config']['Env'])
    check('API selects Jena', env.get('OLDAP_BACKEND') == 'jena')
    check('GraphDB is stopped', not state['graphdb']['State']['Running'])
    check('Private Jena backend has no published ports',
          not any(state['compose-oldap-jena-1']['NetworkSettings']['Ports'].values()))
    for name in ('oldap-api', 'compose-oldap-jena-1', 'compose-oldap-jena-identity-1', 'redis', 'caddy'):
        check(name + ' running', state[name]['State']['Running'])
    report['images'] = {name: item['Config']['Image'] for name, item in state.items()}
    api('/status')
    # Keep the username out of diagnostic check labels as well as the report.
    status, content = request('http://api.home.org/admin/auth/' + quote(env['OLDAP_AUTH_ADMIN_USER'], safe=''),
                              {'password': env['OLDAP_AUTH_ADMIN_PASSWORD']})
    check('Existing administrator can log in', status == 200 and 'accessToken' in json.loads(content))
    admin_token = json.loads(content)['accessToken']
    # No project/file fields: the handler must pass token verification and stop
    # at form validation, before any database or filesystem write can happen.
    status, content = request('http://media.home.org/upload', {}, admin_token)
    check('Media upload accepts a fresh API token before form validation',
          status == 400 and json.loads(content).get('message') == 'Missing projectId field')
    for invalid_token in (None, 'invalid-acceptance-token'):
        status, _ = request('http://media.home.org/upload', {}, invalid_token)
        check('Media upload rejects missing or invalid access token', status == 401)
    public = api('/admin/auth/unknown', {})['accessToken']
    for method_body in (None, {}):
        status, _ = request('http://api.home.org/internal/jena/identity', method_body)
        check('Proxy blocks private identity callback', status == 404)
    status, _ = request('http://api.home.org/internal/export-claims', {})
    check('Export worker route reaches service authentication without proxy shadowing', status == 401)
    stories = api('/data/search/fasnacht/class/fasnacht:Story', {
        'includeProperties': ['fasnacht:storyTitle', 'fasnacht:storyDate', 'fasnacht:isPublished',
                              'fasnacht:leadImage', 'fasnacht:leadImageRegion', 'fasnacht:storyKeywords', 'schema:abstract'],
        'filter': [{'property': 'fasnacht:isPublished', 'op': '==', 'value': True, 'type': 'boolean'}],
        'sortBy': ['fasnacht:storyDate|desc'], 'limit': 1000}, public)
    report['stories'] = len(stories)
    report['stories_sha256'] = hashlib.sha256(json.dumps(normalized(stories), sort_keys=True).encode()).hexdigest()
    report['stories_semantic_sha256'] = hashlib.sha256(json.dumps(normalized_stories(stories), sort_keys=True).encode()).hexdigest()
    if expected_semantic_stories:
        check('Story content equals old-image baseline after keyword IRI expansion',
              report['stories_semantic_sha256'] == expected_semantic_stories)
    if expected_stories:
        check('All story response content equals frozen source baseline', report['stories_sha256'] == expected_stories)
    matches = []
    for term in ('Laterne Stamm', 'Stamm Laterne'):
        rows = api('/data/search/fasnacht', {'ftfilter': [{'field': 'archiveObjectTitle', 'query': term}],
                   'includeProperties': ['schema:name'], 'limit': 100}, public)
        matches.append(normalized(rows))
    check('Nonempty fulltext AND search is independent of word order', bool(matches[0]) and matches[0] == matches[1])
    report['fulltext_matches'] = len(matches[0])
    asset = 'bmg_archive_0024_001_stamm_1912_fotos_fasnacht_004'
    media = api('/data/mediaobject/id/' + asset, token=public)
    # Always use the authorized home host, never a URL supplied by RDF metadata.
    base = 'http://media.home.org/iiif/3/' + quote(asset, safe='')
    query = '?' + urlencode({'token': media['token']})
    status, content = request(base + '/info.json' + query)
    check('Signed IIIF metadata delivered by home media service', status == 200 and 'width' in json.loads(content))
    status, content = request(base + '/full/!160,160/0/default.jpg' + query)
    check('Signed image delivered as JPEG', status == 200 and content.startswith(b'\xff\xd8\xff'))
    report['image_bytes'] = len(content)
    for host in ('fasnacht.home.org', 'app.home.org'):
        check(host + ' page available', request('http://' + host)[0] == 200)
    report['status'] = 'passed'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-stories-sha256')
    parser.add_argument('--expected-stories-semantic-sha256')
    args = parser.parse_args()
    print(json.dumps(run(args.expected_stories_sha256, args.expected_stories_semantic_sha256), indent=2))
