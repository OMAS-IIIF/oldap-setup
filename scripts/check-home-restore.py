#!/usr/bin/env python3
"""Run read-only restore acceptance inside an API container; never print tokens.

Defaults target the isolated network. For a live reference run, supply only the
media URLs via RESTORE_MEDIA_URL and RESTORE_IIIF_URL. Credentials come from that
container's environment. RESTORE_BACKEND=graphdb compares single-word searches;
the legacy query builder does not have the new Jena multiword AND semantics. Login affects only its own Redis session state.
"""
import hashlib
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def normalize(value):
    """Ignore JSON collection ordering, preserving values for the raw digest."""
    if isinstance(value, dict):
        return {k:normalize(v) for k,v in sorted(value.items())}
    if isinstance(value,list):
        return sorted((normalize(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    return value


def digest(value):
    """Hash a response without depending on dictionary or result ordering."""
    return hashlib.sha256(json.dumps(normalize(value),sort_keys=True).encode()).hexdigest()


def canonical_stories(stories):
    """Expand this fixture's list QNames, only in the typed keyword property.

    Worker-local namespace contexts can serialize list references either as
    QNames or full IRIs. Keep the raw digest as evidence; compare the equivalent
    RDF identifiers separately, without rewriting arbitrary literal strings.
    """
    result = []
    for story in stories:
        row = dict(story)
        if 'fasnacht:storyKeywords' in row:
            row['fasnacht:storyKeywords'] = [
                'http://fasnacht.digital/ns/StoryKeywords#' + value.split(':', 1)[1]
                if isinstance(value, str) and value.startswith('L-StoryKeywords:') else value
                for value in row['fasnacht:storyKeywords']
            ]
        result.append(row)
    return result


def run():
    """Check login, restored permissions, stories, archive, fulltext and signed media."""
    api='http://127.0.0.1:8000'
    media=os.getenv('RESTORE_MEDIA_URL','http://oldap-mediahelper:8000')
    iiif=os.getenv('RESTORE_IIIF_URL','http://oldap-imageserver:8182/iiif/3')
    checks=[]; report={'checks':checks}
    def check(label,condition):
        if not condition:raise RuntimeError(label)
        checks.append(label)
    def request(url,body=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urlopen(req,timeout=90) as response:return response.status,response.read()
        except HTTPError as exc:return exc.code,exc.read()
    def data(path,body=None,token=None):
        status,content=request(api+path,body,token)
        label = '/admin/auth/[account]' if path.startswith('/admin/auth/') else path.split('?')[0]
        check('API '+label+' returns 200',status==200)
        return json.loads(content)
    data('/status')
    admin=data('/admin/auth/'+quote(os.environ['OLDAP_AUTH_ADMIN_USER'],safe=''),
               {'password':os.environ['OLDAP_AUTH_ADMIN_PASSWORD']})['accessToken']
    public=data('/admin/auth/unknown',{})['accessToken']
    # Compare the capability result without recording account details or tokens.
    for label,token in [('admin',admin),('public',public)]:
        caps=data('/archive/fasnacht/publication/capabilities',token=token)
        report[label+'_capabilities_sha256']=digest(caps)
        if label=='admin':admin_caps=caps
        else:public_caps=caps
    check('Publication capabilities distinguish administrator and public user',admin_caps!=public_caps)
    for token in (None,'invalid-restore-test-token'):
        check('Upload rejects absent/invalid token',request(media+'/upload',{},token)[0]==401)
    status,body=request(media+'/upload',{},admin)
    check('Fresh restored token accepted before form validation',status==400 and json.loads(body).get('message')=='Missing projectId field')
    stories=data('/data/search/fasnacht/class/fasnacht:Story',{
        'includeProperties':['fasnacht:storyTitle','fasnacht:storyDate','fasnacht:isPublished',
                             'fasnacht:leadImage','fasnacht:leadImageRegion','fasnacht:storyKeywords','schema:abstract'],
        'filter':[{'property':'fasnacht:isPublished','op':'==','value':True,'type':'boolean'}],
        'sortBy':['fasnacht:storyDate|desc'],'limit':1000},public)
    report.update(stories=len(stories), stories_sha256=digest(stories),
                  stories_rdf_sha256=digest(canonical_stories(stories)))
    objects=data('/data/search/fasnacht/class/fasnacht:ArchiveObject',
                 {'includeProperties':['schema:name'],'limit':100,'sortBy':['schema:name']},public)
    check('Archive overview has results',bool(objects))
    report.update(archive_objects=len(objects),archive_sha256=digest(objects))
    backend = os.getenv('RESTORE_BACKEND', 'jena')
    check('Supported comparison backend', backend in {'jena', 'graphdb'})
    # Compare the old installation with its restored copy using unchanged single
    # words. Its multiword query scopes only the first word to the selected field;
    # Jena's deliberately improved AND semantics require a separate acceptance.
    terms = ('Laterne', 'Stamm') if backend == 'graphdb' else ('Laterne Stamm', 'Stamm Laterne')
    hits=[data('/data/search/fasnacht',{'ftfilter':[{'field':'archiveObjectTitle','query':term}],
          'includeProperties':['schema:name'],'limit':100},public) for term in terms]
    if backend == 'graphdb':
        check('Source single-word fulltext searches have results', all(hits))
    else:
        check('Fulltext AND results nonempty and word-order independent',bool(hits[0]) and normalize(hits[0])==normalize(hits[1]))
    report.update(fulltext_matches=len(hits[0]),fulltext_sha256=digest(hits[0]),
                  fulltext_cases=[{'query':term, 'count':len(rows), 'sha256':digest(rows)} for term,rows in zip(terms,hits)])
    asset='bmg_archive_0024_001_stamm_1912_fotos_fasnacht_004'
    token=data('/data/mediaobject/id/'+asset,token=public)['token']
    base=iiif+'/'+asset; query='?'+urlencode({'token':token})
    status,body=request(base+'/info.json'+query)
    check('Restored signed IIIF metadata',status==200 and 'width' in json.loads(body))
    report['iiif_dimensions']={k:json.loads(body)[k] for k in ('width','height')}
    status,body=request(base+'/full/!160,160/0/default.jpg'+query)
    check('Restored signed JPEG',status==200 and body.startswith(b'\xff\xd8\xff'))
    report.update(image_bytes=len(body),image_sha256=hashlib.sha256(body).hexdigest(),status='passed')
    return report


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
