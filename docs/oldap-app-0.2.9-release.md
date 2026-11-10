# OLDAP App 0.2.9 release — 2026-11-10

The owner explicitly accepted deploying the current application despite its known
functional defects and incomplete workflows. This release includes the reviewed
SHACL inversePath correction; the wider product review remains separate.

## Immutable artifact

- Source release commit: oldap-app `f67cbc2` (runtime correction `a766113`).
- Published tag: `lrosenth/oldap-app:v0.2.9` (no latest tag changed).
- Index: `sha256:0a5bd7223775fda5e40df78cbeaf08158cec7a3fceed2586e7a3c735741466a9`.
- AMD64: `sha256:294eeb9fff3efa2b66ec8f7665c0f47726634c8f2094fab9772d98e17bc75b29`.
- ARM64: `sha256:750efe4b5de37bdc203aa8428f7c9aecfa5c0717f09673d82b9bcb87e28f8197`.

Built from a clean Git archive; both target architectures started locally,
reported package version 0.2.9 and served the HTML application with HTTP 200.
The same images were published without rebuilding. Prior source checks: 21
unit/component tests, four mocked browser workflows, build/typecheck and eleven
read-only production Jena API probes. These checks are not whole-product acceptance.

## Deployment and rollback

Use partial selection `releases/oldap-app-0.2.9.json` with the shared
plan-vm/deploy-vm or plan-home/deploy-home targets and protected credentials.
Only oldap-app is selected; no migration or other application update is needed.

Production: applied successfully, runtime 0.2.9 and existing public/internal API
origins verified. Only oldap-app replaced; seven sibling container IDs unchanged.
Public HTTP 200, API/Jena health and browser-rendered application shell pass.
Authenticated edits/uploads were not repeated.

- Private configuration rollback: `/opt/oldap/compose/routine-update-20261110T214117347473Z`.
- Previous production image: `lrosenth/oldap-app@sha256:ab26ef04108cf37980aa542ff36ed7757d9966ea4a704b28faba5e01210c6061`.
- Image-only rollback: select that previous digest in a partial release JSON and
  apply through the shared updater; do not restore the database.
- Home deployment also completed successfully with the exact same image digest.
  Runtime 0.2.9 and home API origins verified; public HTTP/API health and browser
  shell pass. Only oldap-app replaced; seven sibling container IDs retained.
- Home configuration rollback: `/opt/oldap/compose/routine-update-20261110T214828714837Z`.
- Previous home image: `lrosenth/oldap-app@sha256:ad3308b9e4c18054ed431e24ebec953efcfd5253fc910a39014da9ace28220e7`.

Private build/smoke/deployment logs are under
`~/Library/Application Support/OLDAP/releases/oldap-app-0.2.9` on the control machine.
