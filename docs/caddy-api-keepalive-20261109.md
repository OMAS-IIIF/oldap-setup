# Intermittent API 502 responses on home

## Evidence and diagnosis

Caddy reported `connection reset by peer` and `broken pipe` while forwarding
archive search POST requests to `oldap-api:8000`. The API container had zero
restarts and no OOM flag; Gunicorn's four gthread workers had no logged restarts,
worker timeouts or request tracebacks around these failures. This points to the
HTTP connection boundary rather than a demonstrated Fuseki query failure.

The active API command uses Gunicorn 26.0.0, four workers and two threads, without
a keepalive override (default 2 seconds). Caddy's unconfigured HTTP transport
keeps idle connections for 2 minutes. The upstream therefore retires connections
before the proxy. Caddy documents precisely this mismatch as a possible cause
of connection-reset errors and 502 responses for non-idempotent requests; search
uses POST even though it reads data. See the official
[Caddy HTTP transport documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#the-http-transport).

## Change and scope

Set `transport http { keepalive 1s }` only on the OLDAP API upstream. Keepalive
remains enabled within bursts but the proxy retires idle connections before
Gunicorn. No blanket POST retries, longer request timeouts or database changes.
The canonical `templates/Caddyfile.j2` covers home, production and the optional
SALSAH API alias. The legacy root Caddy template is kept consistent.

On home the existing configuration was patched narrowly, validated inside the
running Caddy container and reloaded at 2026-11-09 22:02:50 UTC. The bind-mounted
file was updated in place so its inode remains visible to the container. No API,
Jena or frontend container was replaced. Existing TLS/console/SALSAH settings
were preserved. Production has not been changed.

Rollback copy:
`/opt/oldap/compose/Caddyfile.before-keepalive-20261109T230246`.
Restore its contents into the existing Caddyfile inode and run
`docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
Do not replace the file atomically without considering the single-file bind mount.

## Verification

- Candidate configuration passes `caddy validate`; reload succeeds.
- Live Caddy admin JSON confirms 1,000,000,000 ns idle timeout on both home API
  routes (HTTP and HTTPS).
- 14 existing Jena/SALSAH deployment tests pass using the installed Ansible Python
  environment. The initial system-Python invocation lacked Jinja2; no dependencies
  were installed or changed to address that harness issue.
- The final matched frontend comparison captured 552 API responses without HTTP
  errors, alongside token-renewal/error-injection and named/public reader smoke
  tests. Deliberately browser-injected failures are not server failures.
- Caddy recorded no new 5xx responses between reload and the final check at
  22:13:26 UTC, including fresh contexts and repeated bursts with idle intervals.

The observed mismatch and successful checks support this diagnosis; this short
window cannot prove the absence of all future 502 causes. Keep normal monitoring.
A separate recurring API log message reports missing mobile-media lifecycle
credentials; it is not a worker crash and was not changed in this task.

Private deployment play/log and browser probes:
`~/Library/Application Support/OLDAP-Jena/probes/archive-metadata-implementation/`.

## Subsequent production promotion

The same narrowly scoped transport correction was validated and reloaded on
production with FasnachtsPage 0.1.50. Live settings, observation and independent
rollback are recorded in [the production release report](fasnacht-0.1.50-production-20261109.md).
