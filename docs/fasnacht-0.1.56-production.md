# FasnachtsPage 0.1.56 production deployment

Production fasnacht.digital now runs 0.1.56 with oldap-guilib 0.0.28. The
published AMD64/ARM64 image passed version, library version and six-route checks.
Only fasnachts-page was replaced; seven peer containers, media services, Home,
configuration outside the selected image, and archive data remain unchanged.

Chromium and WebKit both pass the live stories check across five viewport widths
without ResizeObserver or other page errors. Injected image 403 recovery and
visible image loading pass in both engines. Final deployment plan is unchanged.

See [receipt](fasnacht-0.1.56-production-results.json),
[selection](../releases/production-fasnacht-0.1.56.json) and
[rollback](../releases/production-fasnacht-0.1.56-rollback.json).
Rollback to 0.1.55 uses plan-vm/deploy-vm with the explicit rollback selection
and the protected production become-vars file. Private configuration backup:
`/opt/oldap/compose/routine-update-20261125T223250015651Z`. No database restore or media-policy change is required.
