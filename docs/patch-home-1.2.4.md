# Home patch 1.2.4

Home now runs the production-accepted API/identity 1.2.4 and selects on-demand
tools 1.2.3, both with oldaplib 1.2.3. Only API/identity containers changed.
Jena, Redis, frontends and harvester selections remain unchanged. No imports,
business-data writes or production changes were performed.

Health and archive HTTPS pass. Public/authenticated reads each verify 20 media,
three linked entries and title/extracted-text fulltext results. Tools image
versions are verified offline. Final plan reports no configuration changes.

Reapply using `make deploy-home RELEASE_FILE="$PWD/releases/home-1.2.4.json"`;
rollback uses the same target with `releases/home-1.2.4-rollback.json`.
Use the established protected become-vars file or sudo prompt.
See [receipt](patch-home-1.2.4-results.json) for image digests and backup location.
