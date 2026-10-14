# Frontend Documentation

## Structure

ai-dashboard/
    index.html
    css/style.css
    js/app.js

## Panels

- Chat Interface
- Models
- System Monitor
- Virtual Machines
- Network Services
- Discord Bot
- Settings

## Key Features

- Internal scrolling chat window
- Fixed input bar
- Saved conversations for the signed-in account, with resume, new-chat, and
  confirmed delete controls; the most recently updated chat resumes after
  sign-in
- Admin-only shared operational notes with explicit publish/remove
  confirmations, distinct from private chat transcripts
- Sidebar navigation
- VM planning interface with a truthful empty inventory state, guest-detail
  layout, and an unavailable recovery-console placeholder
- Network-service planning views for DHCPv4, DHCPv6, DNS, web hosting, and
  routing/firewall, including undecided configuration and safety boundaries
- Backend online/offline indicator
- Model cards discovered from installed GGUF files, with load status and file size
- Explicit web-research toggle and source links for research answers
- System monitor with animated bars
- Discord bot log viewer

## JavaScript Responsibilities

- Poll backend for telemetry
- Send chat messages
- Load and render persisted conversation turns and research source links; pass
  the selected conversation ID to REST and WebSocket chat requests
- Load shared notes only for admins; render note content with text nodes and
  require explicit confirmation before publishing or removing notes
- Refresh conversation titles/message counts after each completed or failed
  turn; never put chat content in browser storage
- Update UI panels
- VM and network-service panels are UI groundwork only: do not display sample
  inventory as live state or send management requests until backend providers,
  role checks, and deployment configuration exist
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
