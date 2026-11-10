# API image builds from the consolidated OLDAP tree

Run from `OLDAP/oldap-api`. Use one new absolute bundle directory outside Git;
spaces are supported. The commands delegate to sibling `oldap-setup` and use its
allowlisted wheel-only build context and pinned Python base image.

```sh
make docker-prepare IMAGE_BUNDLE=/absolute/new-bundle
make docker-image IMAGE_BUNDLE=/absolute/new-bundle
make docker-accept IMAGE_BUNDLE=/absolute/new-bundle \
  JENA_SERVICE_RELEASE=/absolute/existing-built-jena-service
make docker-push IMAGE_BUNDLE=/absolute/new-bundle
```

`docker-build` is an alias of `docker-image`. Prepare creates the bundle once;
build does not implicitly replace its inputs. Acceptance exercises installed API
images against an isolated temporary real Jena dataset, with no published ports.
Publish requires acceptance matching the exact image IDs and refuses existing
registry tags. It never rebuilds, deploys or uploads Python packages.

The default produces fingerprinted candidates, allowing uncommitted development
sources. For a final release, commit the relevant sources first and add
`IMAGE_FINAL=true` to **prepare**. Stable API and library versions may differ,
but the library must satisfy the application's declared dependency range.
Final preparation refuses dirty source trees and prerelease versions.

Use `IMAGE_CONSTRAINTS=/absolute/accepted-constraints.txt` at preparation to retain
an accepted third-party dependency set. Otherwise dependencies resolve during
build and must be reviewed before promotion. Both amd64 and arm64 are built and
checked for installed versions, Jena imports and `pip check`.

Setup exposes equivalent `image-prepare`, `image-build`, `image-accept`, and
`image-publish` targets. `IMAGE_COMPONENT` defaults to `oldap-api`; selecting
`oldap-tools` prepares tools plus the library only. Tools acceptance covers its
packaged startup/import/user contract; API-backed tools operations require their
own functional acceptance. The API's Make wrapper always selects the API.

After publication, explicitly place reviewed registry digests in a deployment
release file and use `make plan-home` / `make deploy-home` in setup. Build output
never automatically changes `releases/current.json` or running services.

The old API Dockerfile and `docker-run` are legacy paths; this workflow does not
use either. Local native Jena service installation is a separate next step.

## Acceptance on 2026-11-10

43 focused tests passed. A real API-only candidate was prepared from OLDAP and
built for AMD64 and ARM64. Both installed images passed version/import/dependency
checks and real isolated Jena transaction, persistence, identity and network
isolation acceptance through `make docker-accept`. Test containers were removed.
No registry publication or deployment occurred. See `image-build-workflow-results.json`.
Private bundle/logs: `~/Library/Application Support/OLDAP/releases/20261110-make-workflow`.
