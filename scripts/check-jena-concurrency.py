"""Read-only home archive acceptance under competing API requests.

Establish sequential response baselines, then overlap archive, taxonomy, user
and story reads at greater concurrency than the public API worker pool. This
reproduces callback starvation without changing data or printing credentials.
Run on api.home.org with Python's standard library; writes only JSON to stdout.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


# Exact list namespaces from the frozen home export, restricted to IRI-valued
# properties. Workers can learn list prefixes at different times; a QName and
# its full IRI name the same resource. Never rewrite arbitrary text literals.
LIST_PROPERTIES = {
    'fasnacht:carnivalPractice': ('CarnivalPracticeTaxonomy',),
    'fasnacht:organisationTaxonomy': ('OrganisationTaxonomy',),
    'fasnacht:representationRole': ('MediumRepresentationTaxonomy',),
    'dcterms:rights': ('CreativeCommons',),
    'dcterms:type': ('ObjectTaxonomy', 'CarnivalEventTaxonomy'),
}


def normalized(value, property_name=None):
    """Compare unordered RDF results and known equivalent list IRI spellings."""
    if isinstance(value, dict):
        return {key: normalized(item, key) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((normalized(item, property_name) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, str):
        for name in LIST_PROPERTIES.get(property_name, ()):
            prefix = 'L-' + name + ':'
            if value.startswith(prefix):
                return 'http://fasnacht.digital/ns/' + name + '#' + value[len(prefix):]
    return value


def archive_cases():
    """Return representative initial-load requests used by the archive page."""
    common = ['schema:name', 'schema:description', 'dcterms:type',
              'fasnacht:carnivalPractice', 'fasnacht:associatedOrganisation']
    fields = {
        'ArchiveMediaObject': common + ['fasnacht:creationDating', 'fasnacht:location',
            'dcterms:creator', 'fasnacht:contributingAgent', 'shared:mediaAccessMode',
            'dcterms:rights', 'fasnacht:rightsStatementUrl', 'fasnacht:representationRole',
            'fasnacht:archiveMediaObjectOf', 'schema:position', 'shared:originalMimeType', 'shared:assetId'],
        'ArchiveObject': common + ['fasnacht:dating', 'fasnacht:location', 'dcterms:creator',
                                  'fasnacht:currentCustodian', 'fasnacht:externalSource'],
        'CarnivalEvent': common + ['fasnacht:dating', 'fasnacht:location', 'dcterms:creator', 'fasnacht:externalSource'],
        'Agent': ['schema:familyName', 'schema:givenName', 'schema:name'],
        'Person': ['schema:familyName', 'schema:givenName', 'schema:name'],
        'Organisation': ['schema:name', 'fasnacht:organisationTaxonomy'],
        'ExternalSource': ['schema:name', 'fasnacht:lastHarvest'],
        'Story': ['fasnacht:storyTitle', 'fasnacht:storyDate', 'fasnacht:isPublished'],
    }
    cases = [(name, '/data/search/fasnacht/class/fasnacht:' + name,
              {'includeProperties': properties, 'limit': 5000}) for name, properties in fields.items()]
    cases.extend((name, '/admin/hlist/fasnacht/' + name, None) for name in
                 ('ObjectTaxonomy', 'CarnivalEventTaxonomy', 'OrganisationTaxonomy'))
    cases.append(('anonymous-profile', '/admin/user/unknown', None))
    return cases


def run():
    """Compare complete responses at 16-way concurrency; return sanitized evidence."""
    base = 'http://api.home.org'
    with urlopen(Request(base + '/admin/auth/unknown', data=b'{}',
                         headers={'Content-Type': 'application/json'}), timeout=30) as response:
        token = json.loads(response.read())['accessToken']

    def read(case):
        label, path, body = case
        request = Request(base + path, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        started = time.monotonic()
        try:
            with urlopen(request, timeout=60) as response:
                value = json.loads(response.read())
                digest = hashlib.sha256(json.dumps(normalized(value), sort_keys=True).encode()).hexdigest()
                return {'case': label, 'status': response.status, 'sha256': digest,
                        'seconds': round(time.monotonic() - started, 3)}
        except HTTPError as error:
            return {'case': label, 'status': error.code}

    cases = archive_cases()
    baseline = [read(case) for case in cases]
    if any(row['status'] != 200 for row in baseline):
        return {'status': 'failed', 'phase': 'sequential', 'results': baseline}
    expected = {row['case']: row['sha256'] for row in baseline}
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(read, cases * 4))
    passed = all(row['status'] == 200 and row.get('sha256') == expected[row['case']] for row in results)
    return {'status': 'passed' if passed else 'failed', 'concurrency': 16,
            'comparison': 'array ordering and reviewed list QName/full-IRI equivalence; all values retained',
            'sequential_baselines': baseline, 'parallel_requests': len(results),
            'http_status_counts': dict(Counter(row['status'] for row in results)),
            'complete_responses_match': passed, 'results': results}


if __name__ == '__main__':
    report = run()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'passed' else 1)
