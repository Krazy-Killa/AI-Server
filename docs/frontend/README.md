# Frontend Documentation

## Structure

ai-dashboard/
    index.html
    css/style.css
    js/
        app.js
        backend-logs.js
        operations.js
        system-monitor.js
        theme-init.js
        ui-preferences.js

`index.html` loads `js/app.js` as a native ES-module entry point; the dashboard
uses browser modules directly and does not require a bundler. The entry point
owns authentication, navigation, chat/research, model selection, and bot
controls. Focused modules own backend logs, observe-only diagnostics and
Proxmox inventory, system telemetry, and persisted UI preferences. Modules
exchange shared API/auth and UI state through explicit imports or initializer
arguments rather than classic-script globals. Serve the dashboard over HTTP or
HTTPS so browsers can load its module imports.

## Browser security headers

The dashboard has no inline scripts, inline event handlers, or `style`
attributes, so it can be served under a strict Content-Security-Policy.
`js/theme-init.js` is the small classic script that applies the saved light
theme before first paint. Keep new code in external modules.

[`ai-backend/dashboard_server.py`](../../ai-backend/dashboard_server.py)
defines the policy (`script-src 'self'`, `default-src 'none'`,
`frame-ancestors 'none'`, `connect-src` limited to the dashboard origin and
port `8000`) plus `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`,
and `Cache-Control: no-store`. It serves only `index.html`,
`manifest.webmanifest`, `css/` (including `css/fonts/`), `icons/`, and `js/`
with directory listings disabled. The Quadlet dashboard unit,
`run-dashboard.bat`, and `lan_dashboard_server.py` use it; the Playwright
static server sends an equivalent policy and the module-loading test fails on
any policy violation. Fonts (Barlow Condensed, DM Mono and Manrope, Latin
subsets under the SIL Open Font License) are self-hosted in `css/fonts/`, so
the policy allows no third-party origins (`style-src 'self'`,
`font-src 'self'`, `manifest-src 'self'`). A `window.AI_SERVER_API_BASE`
override to another origin or port must also be added to `connect-src`.
HSTS and TLS headers are sent by the NGINX proxy, not by this server.

### Mobile and installable-app behavior

- The header and System-card CPU values are live (`#cpu-header`, `#cpu-value`)
  and show `N/A` when telemetry is missing or the backend is unreachable.
- `js/visibility.js` (`setVisibleInterval`) pauses every polling timer while
  the browser tab is hidden and refreshes once when it becomes visible again.
- A red banner (`#connection-banner`) appears when the backend status poll
  fails and clears when it recovers. An expired session still returns to the
  sign-in screen with its own notice.
- On phones, the smallest 9-10px labels are raised to 11-12px, and on
  touch devices form fields use 16px text so iOS Safari does not zoom on
  focus. Pinch zoom is not disabled.
- The Diagnostics header stacks on phones: the status pill sits on its own
  row above the full-width Refresh, Download report and Run observation
  buttons. Where native file sharing is supported (including the iOS
  Home Screen app), the report is prepared before the tap and opens the
  system share sheet; choose Save to Files to keep it. Browsers without
  supported file sharing retain the regular file-download behavior. The iOS
  Home Screen flow is feature-detected and covered with a mocked Playwright
  test; it still needs on-device verification after deployment.
- `manifest.webmanifest` and `icons/` (SVG, 192/512 PNG, 180 px Apple touch
  icon) let phones add the dashboard to the home screen in standalone mode.
  This does not add offline support or a service worker. Verified on an
  iPhone against the nested lab; the device must trust the lab certificate
  authority, or iOS shows a letter instead of the icon.
  These assets are deployed and were verified on an iPhone against the nested
  lab. The newer Diagnostics share-sheet change has not yet been deployed or
  verified on the phone.

## Browser regression tests

The Playwright suite in `tests/frontend/` serves the dashboard's allowlisted
assets over local HTTP and mocks API responses in the browser. It checks native
module loading, pre-authentication request gating, successful and rejected
sign-in, role-specific controls, panel navigation, persisted
theme/accent/sidebar preferences, VM inventory rendering, signed-bundle
staging controls, and Diagnostics report download/share behavior.
These are frontend regressions, not backend authentication tests or Proxmox
integration evidence. See the [Windows testing guide](../operations/testing-environment.md#dashboard-browser-regressions)
for setup and execution.

## Panels

- AI Interface (single shared admin server console)
- AI Chat (private per-account conversations and optional web research)
- Models
- System Monitor
- Virtual Machines (read-only inventory table: one 12 px cell scale, monospace
  VMID and node, and a power-state pill with a status dot; on screens up to
  560 px wide each guest becomes a compact two-column card instead of scrolling
  sideways; on phones the stat tiles sit two per row)
- Network Services
- Discord Bot
- Settings, organized as sub-tabs: Appearance (theme, accent), Account
  (signed-in identity and Sign out, which is the only sign-out on phone
  layouts because the sidebar footer is hidden there),
  Network & Access (read-only origin and HTTPS status), Models and Diagnostics
  (links to their panels), About, and an admin-only Setup / Deployment tab
- Setup / Deployment contains the **Firmware File** picker and Verify button
  (verify-only, Stage 1). Opening the tab checks `GET /api/admin/updates`; the
  controls stay disabled with an explanation when no signing key is configured
  on the server. A chosen `.aibundle` is uploaded raw with the CSRF header and
  the verified release (ID, version, signer, payload digest, size, expiry) is
  listed with a Discard button. Apply is always disabled: applying is done at
  the console with the operator runbook (`js/release-updates.js`).
- A conversational household voice interface is a future concept; local STT/TTS
  and voice-driven requests are not implemented

## Key Features

- Internal scrolling chat window
- Fixed input bar that stays visible at the bottom of AI Interface and AI Chat
  on mobile; the app header and navigation remain in fixed viewport rows while
  panel content scrolls independently. Portrait controls use compact rows;
  landscape keeps chat controls horizontal, places Research Web beside the
  input, and trims vertical spacing to preserve conversation space. Transmit
  stays beside the input.
- AI Interface uses one persistent admin-shared operational transcript, with
  admin attribution and a persistent notice that turns are visible to all
  administrators; the notice can be dismissed until the page is reloaded
- AI Chat keeps saved conversations scoped to the signed-in account, with
  resume, new-chat, and confirmed delete controls; the most recently updated
  chat resumes after sign-in
- Admin-only shared operational notes with explicit publish/remove
  confirmations, distinct from private chat transcripts
- Sidebar navigation
- The sidebar toggle collapses the navigation on desktop and tablet layouts;
  collapsed desktop mode keeps navigation icons centered in the sidebar rail,
  while collapsed tablet mode hides the full-width navigation row. Compact
  phone and short-landscape layouts use full-width horizontal navigation
  without the sidebar toggle.
- Tablets from 761px through 1200px wide and taller than 600px use full-width
  navigation grids: landscape uses six columns (two rows for the current
  workspace links) and portrait uses four columns. The header toggle hides or
  restores this navigation row.
- Read-only VM/container inventory loaded from the backend Proxmox provider on
  panel open or explicit refresh; unavailable/configuration failures are shown
  as status, and guest data is rendered as text with human-readable power states
- Inventory scope is explicit; VM management and guest-console controls are not
  exposed
- Network-service planning views for DHCPv4, DHCPv6, DNS, web hosting, and
  routing/firewall, including undecided configuration and safety boundaries.
  Future service monitoring may cover daemons hosted inside VMs, but its first
  integration is observe-only and must not expose service or network changes.
- Backend online/offline indicator
- Sidebar host name and detected GPU adapter from `/api/system`; shows DIAG
  during an active observation, MAINT when the API reports active maintenance,
  otherwise CONSOLE while AI Interface is selected or reflects the Research
  Web toggle in AI Chat. MAINT is not yet emitted because the maintenance
  lifecycle is not implemented.
- Model cards discovered from installed GGUF files, with load status and file size
- Explicit web-research toggle and source links for research answers
- System monitor with animated bars
- System Monitor presents GPU load, live VRAM, CPU, and RAM in a responsive
  two-column metric-card grid that collapses to one column on very narrow
  screens
- Discord bot log viewer

## JavaScript Responsibilities

- Poll backend for telemetry
- Load the dashboard entry point and its focused native ES modules
- Send server-interface requests through the admin-only shared console API;
  render persisted shared messages with administrator attribution
- Send AI Chat messages and optional research requests; keep their saved
  conversation selection separate from the shared server console
- Load and render persisted conversation turns and research source links; pass
  the selected conversation ID to REST, WebSocket chat, and Server-Sent Event
  research requests
- Stream research tokens while retaining returned citation links and
  distinguishing sources with fetched page text from excerpt-only fallbacks
- Load shared notes only for admins; render note content with text nodes and
  require explicit confirmation before publishing or removing notes
- Refresh conversation titles/message counts after each completed or failed
  turn; never put chat content in browser storage
- Update UI panels
- Send only authenticated, read-only VM inventory requests to the backend;
  Proxmox API credentials remain server-side. No create, power, snapshot,
  configuration, or console requests are implemented. Network-service panels
  remain planning UI.
- Show the active model and list installed models; unloaded entries cannot be selected
- Display logs
- Manage theme/accent colors
- Check the backend session before revealing the dashboard, submit local or
  Proxmox credentials without persisting them, and support logout/expiry states
- Include session cookies and CSRF tokens in authenticated API requests; never
  store credentials, session IDs, or CSRF tokens in browser storage
- Hide or disable controls that exceed the signed-in user's dashboard role;
  the backend remains the enforcement boundary
- Use the local `:8000` backend when the development dashboard is on `:8001`,
  same-origin API/WebSocket URLs behind a production proxy, and an optional
  `window.AI_SERVER_API_BASE` override
- Network-service UI remains a planning view. Network-aware diagnostics are
  an unscheduled concept; no network telemetry integration or diagnostic
  workflow is implemented. See the
  [roadmap candidate](../roadmap/README.md#candidate-backlog--not-scheduled).
- The conversational household interface is also an unscheduled concept.
  Local speech recognition/synthesis, household-member authorization, and
  proactive incident notifications are not implemented. Voice must not bypass
  the existing role and approval boundaries; see the
  [roadmap candidate](../roadmap/README.md#candidate-backlog--not-scheduled).
- Planned update UI (Stage 2): after a verified upload (implemented, verify-only),
  display target/compatibility, then require an explicit
  admin confirmation before Apply. Show updater progress, health-check result,
  rollback result, and recovery-needed failures. Never imply success before
  the updater confirms both services healthy. Apply and its endpoints are
  not implemented.
