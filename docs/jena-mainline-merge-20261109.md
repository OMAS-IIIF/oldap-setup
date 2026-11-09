# Jena mainline integration — 2026-11-09

The owner authorized merging the accepted Jena migration after production cutover,
backup recovery and the successful frontend performance rollout. This integration
preserves complete history; it does not deploy, change package versions, publish
1.0.0 artifacts or move existing release/image tags. Core RC metadata remains as
tested. Final release packaging remains a separate task.

## Scope and provenance

All nine migration checkouts were clean before the operation. Origin refs were
refreshed; none of the primary branches had commits absent from the migration.
Every initial merge-tree matched the migration tip exactly. Only codex.md and
CODEX_LOG.md were added to each source integration; setup also records this audit.
The merge parents are the original primary tip and the documented migration tip.
No source conflicts, rebases or squash/cherry-pick shortcuts were needed.

The annotated `pre-jena-merge-20261109` tag in each repository retains its prior
remote primary tip. This is a Git reference, **not** a claim about the production
GraphDB image/source baseline. In particular, oldaplib includes the established
ontology-refactor ancestry beyond its much older main. Keep the actual cutover
baseline, production backups and GraphDB worktrees for historical comparison.
Migration branches are retained; no remote branch deletion or force-push is used.

| Repository | Primary | Previous primary | Reviewed source | Merge |
|---|---|---|---|---|
| oldaplib | main | `c4c618075767` | `3f213a52c78b` | `a7a878ebd80433f50e52343111dfdad14643ced3` |
| oldap-setup | main | `938f7ed656be` | `a8009a39add3` | `recorded in containing merge` |
| oldap-tools | main | `1949fc5015b2` | `a4be9592f3f6` | `7e769aca3f6a3342790a63decf19bfb62980b664` |
| oldap-app | main | `9698a77a602e` | `6c01cc453566` | `4f5d121baa66bb681f89e187d41692378575bd88` |
| FasnachtsPage | master | `c2297fe552f2` | `2116ad8ae94e` | `e0703388b29a42cd280580d0ae2548894991854a` |
| oldap-harvesters | main | `4cc2d1607893` | `460932333540` | `39eda81370d36571c42c5f1934ad7b77fc617dfb` |
| salsah-2 | main | `41fc6c75bf0c` | `a0bb3ff3b70c` | `eaa4d21621d42c3fe6f14d7ccb19a8c3b728e6ff` |
| oldap-api | main | `9d58a12fd443` | `776e70a1f706` | `9d1b6b592cfffecc1eee0447f55d8a6d0a4bc63c` |
| oldap-mediaserver | main | `89be99ddf98a` | `397de927dc8d` | `e8e61d22807dcd83a943940d5101bc6f89f02024` |

Setup's final merge revision is discoverable as the mainline merge containing
this document. Exact remaining revisions and source trees are in the accompanying
JSON inventory. Each repository publishes migration branch, baseline tag and
primary merge atomically. Publication is sequential across repositories; Git
cannot provide a multi-repository atomic transaction. Final remote-ref checks
must pass for all nine before calling the integration complete.

## Verification and automation inspection

- Merge trees equal their documented migration trees; runtime files equal the
  pre-integration reviewed tips. Prior candidate/production acceptance applies to
  that unchanged runtime, not a claim of rerunning every historical test today.
- Required media suite rerun: 391 passed, 20 skipped, four subtests passed. Black
  leaves all 12 changed Python files unchanged; Poetry metadata check passes with
  existing deprecation warnings. The initially selected empty Poetry environment
  lacked pytest; the established complete environment was used successfully.
- Fresh Docker Hub repository inspection reports `is_automated=false` for API,
  Tools, Harvesters, Mediahelper, oldap-app, SALSAH and FasnachtsPage.
- No tracked GitHub workflow files or active local hooks/custom hook paths exist.
  GitHub API lists only managed Dependency Graph workflows in three repositories.
  Hook inspection succeeds with empty lists for the three personal backend repos;
  other hook endpoints return 404 and two ruleset endpoints return 403. Thus full
  organization/external automation visibility is not claimed. Available repository
  permissions permit pushing all nine; standard non-forced pushes enforce GitHub
  protections. No workflow or protection setting is changed.
- Added diff lines were checked for private-key/JWT/GitHub-token patterns with no
  matches. This is a scoped check, not a full historical credential audit.

## Follow-up

Create the final 1.0.0 artifacts only through a separately reviewed release path:
update exact versions/locks and consumer packaging together, test clean artifacts
and retain digest provenance. Do not invoke historical bump/push targets merely
because main now contains Jena. The live immutable candidate images remain valid
and unchanged. Old GraphDB directories are not reset or removed. The API's old
main worktree remains attached to its historical local main; remote main can be
newer without modifying that checkout. Continue current migration checkouts until
an explicit development-directory cleanup is agreed.

GitHub reported 52 Dependabot alerts on oldap-app during the successful push
(2 critical, 23 high, 18 moderate, 9 low). These were not triaged in the merge
operation; follow up separately without assuming all apply to production runtime.
