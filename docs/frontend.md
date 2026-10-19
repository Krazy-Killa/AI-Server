# Frontend Documentation

## Structure

ai-dashboard/
    index.html
    css/style.css
    js/app.js

## Panels

- AI Interface (single shared admin server console)
- AI Chat (private per-account conversations and optional web research)
- Models
- System Monitor
- Virtual Machines
- Network Services
- Discord Bot
- Settings

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
