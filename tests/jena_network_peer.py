"""Owned network acceptance peer, using the real API identity route and token codec.

This deliberately does not initialize a full API or provision user accounts. It
tests the container transport boundary independently of source-data migration.
Never deploy this test HTTP application as an OLDAP API.
"""
import json
import os
import signal
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def serve():
    """Expose only a frontend probe; identity runs in its independent service."""
    from flask import Flask
    # Python is PID 1 in this fixture; explicitly honor Docker's stop signal.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    app = Flask(__name__)
    app.add_url_rule('/network-check', view_func=lambda: 'api-ready')
    app.run(host='0.0.0.0', port=8000, threaded=True)


def transaction():
    """Commit and read one synthetic triple via real token verification."""
    from oldaplib.src.authentication import AuthorizationContext, TokenCodec
    context = AuthorizationContext.from_claims(
        user_id='network-check', user_iri='urn:oldap:network-check',
        claims={'inProject': {}, 'hasRole': {}})
    token = TokenCodec.from_environment().issue_access_token(context)
    base = os.environ['OLDAP_JENA_URL']
    headers = {'Authorization': 'Bearer ' + token,
               'X-Oldap-Service-Key': os.environ['OLDAP_JENA_SERVICE_KEY']}
    identifier = str(uuid4())

    def send(operation, body='', credentials=None):
        with urlopen(Request(base + '/' + operation + '/' + identifier,
                             data=body.encode(), headers=credentials or headers), timeout=10) as response:
            return response.read().decode()

    if os.getenv('CHECK_EXISTING'):
        assert json.loads(send('READ', 'ASK { GRAPH <urn:network:test> { <urn:record> <urn:value> 1 } }'))['boolean']
    send('BEGIN')
    # Import/export polling can overlap: a second writer is refused at BEGIN,
    # before it can modify data. Keep this distinct from uncertain commit errors.
    try:
        urlopen(Request(base + '/BEGIN/' + str(uuid4()), data=b'', headers=headers), timeout=10)
    except HTTPError as error:
        assert error.code == 409
    else:
        raise AssertionError('Concurrent writer admission unexpectedly succeeded')
    print('PASS concurrent BEGIN is explicitly refused with HTTP 409')
    send('UPDATE', 'INSERT DATA { GRAPH <urn:network:test> { <urn:record> <urn:value> 1 } }')
    assert send('COMMIT') == 'committed'
    assert json.loads(send('READ', 'ASK { GRAPH <urn:network:test> { <urn:record> <urn:value> 1 } }'))['boolean']
    for credentials in ({'Authorization': 'Bearer ' + token},
                        {**headers, 'Authorization': 'Bearer invalid'}):
        try:
            send('READ', 'ASK {}', credentials)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError('Invalid credentials accepted')
    print('PASS callback, commit/read, missing transport key, invalid user token')
    admission_retry(token)


def admission_retry(token):
    """Verify real Python admission recovery without replaying a write.

    Synchronize on the first actual refusal, then release the first writer.
    This avoids guessing when a concurrent request reaches the service.
    """
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from oldaplib.src.jena_connection import JenaConnection
    from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists

    holder = JenaConnection(token=token)
    contender = JenaConnection(token=token)
    refused = Event()
    operations = []
    send = contender._send

    def observed_send(operation, *args, **kwargs):
        operations.append(operation)
        try:
            return send(operation, *args, **kwargs)
        except OldapErrorAlreadyExists:
            if operation == 'BEGIN':
                refused.set()
            raise

    contender._send = observed_send
    holder.transaction_start()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(contender.transaction_start)
        try:
            assert refused.wait(timeout=10), 'No real concurrent BEGIN refusal observed'
        finally:
            holder.transaction_abort()
        future.result(timeout=10)
    contender.transaction_update(
        'INSERT DATA { GRAPH <urn:network:test> { <urn:retry> <urn:value> 2 } }')
    contender.transaction_commit()
    assert contender.query('ASK { GRAPH <urn:network:test> { <urn:retry> <urn:value> 2 } }')['boolean']
    assert 2 <= operations.count('BEGIN') <= 5
    assert operations.count('UPDATE') == operations.count('COMMIT') == 1
    print('PASS Python BEGIN retry after real contention; exactly one UPDATE and COMMIT')


def outside():
    """A bridge peer can reach the API alias, but cannot reach private Jena."""
    with urlopen('http://oldap-api:8000/network-check', timeout=5) as response:
        assert response.read() == b'api-ready'
    for port, path in ((3031, '/health'), (8001, '/_ready')):
        try:
            urlopen(f'http://oldap-jena:{port}{path}', timeout=3)
        except URLError:
            pass
        else:
            raise AssertionError(f'Private listener {port} is exposed on the bridge')
    print('PASS API alias reachable; backend and identity unreachable from bridge')


if __name__ == '__main__':
    {'serve': serve, 'transaction': transaction, 'outside': outside}[sys.argv[1]]()
