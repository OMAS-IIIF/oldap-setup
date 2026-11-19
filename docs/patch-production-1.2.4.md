# Production patch 1.2.4

API/identity 1.2.4 now use oldaplib 1.2.3, fixing implicit adoption of existing
superproperties during property insertion. Published tools 1.2.3 use the same
library; production has no tools service. Only API/identity containers changed.

Both image architectures passed 126 installed tests plus two subtests and real
isolated Jena acceptance. Production health, public/authenticated archive and
fulltext checks pass. TGB's original YAML plans zero changes and its required
route reifier reads back correctly. No business-data writes or home changes.

Reapply with `make deploy-vm RELEASE_FILE="$PWD/releases/production-1.2.4.json"`;
rollback with the same target and `releases/production-1.2.4-rollback.json`.
Use the established protected become-vars file or sudo prompt.
Exact digests, rollback directory and validation: [receipt](patch-production-1.2.4-results.json).
