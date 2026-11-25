# FasnachtsPage 0.1.56 on Home

The exact production-accepted AMD64/ARM64 image is active on fasnacht.home.org;
no rebuild. Runtime versions 0.1.56 / oldap-guilib 0.0.28, API/Jena health and
final unchanged plan pass. Only fasnachts-page was recreated; seven peer IDs
are unchanged. Production, media services, data and schedules were not changed.

Chromium and WebKit pass the live stories test across five viewport widths
without ResizeObserver or other page errors. Visible images and recovery from
an injected image 403 pass in both browsers.

See [receipt](fasnacht-0.1.56-home-results.json),
[selection](../releases/home-fasnacht-0.1.56.json) and
[rollback to 0.1.54](../releases/home-fasnacht-0.1.56-rollback.json).
Rollback uses plan-home/deploy-home with the explicit rollback selection and
protected Home become-vars file. Private configuration backup:
`/opt/oldap/compose/routine-update-20261125T224016099665Z`. No database restore is required.
