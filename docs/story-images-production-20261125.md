# Story image fixes on production — 2026-11-25

FasnachtsPage 0.1.55 is active on fasnacht.digital. Its immutable image and the
SIPI external OLDAP policy fix were deployed under the user's authorization.
Only the frontend and imageserver containers were replaced. All seven application
peers and five media peers retained their IDs. API/Jena/mediahelper health passes;
Home, data and schedules were unchanged.

The media policy allows two seconds of JWT clock skew. SIPI remains 1.0.3, with
the tested policy from commit 67ceb2a mounted read-only; oldap-mediaserver commit
c9a2636 retains this selection for future full deployments. Sixteen immediate
fresh-token image requests pass (200); invalid tokens remain denied (403).
Chromium and WebKit both recover an injected image 403 with a new token and load
the visible story images. WebKit still reports the pre-existing ResizeObserver
loop warning; this unrelated layout issue remains open. The user's aged named-user
Safari session was not reproduced. A reload activates the new frontend in old tabs.

See the [sanitized receipt](story-images-production-20261125-results.json),
[selection](../releases/production-story-images-20261125.json) and
[frontend rollback](../releases/production-story-images-20261125-rollback.json).
Final production plan is unchanged. Frontend rollback uses the ordinary plan-vm /
deploy-vm workflow with the rollback selection. Private frontend backup:
`/opt/oldap/compose/routine-update-20261125T220410209712Z`.
Media rollback restores the previous Compose file from
`/opt/oldap-mediaserver/compose/story-policy-20261125T215953Z` and recreates only
imageserver; see oldap-mediaserver docs/sipi-deployment.md. No database restore.
