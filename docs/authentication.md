# Authentication & Session Management

## Status and scope

**Status:** Windows implementation complete and verified by the backend test
suite, including mocked Proxmox responses. No production/Proxmox-host or
HTTPS-proxy validation has been performed.

The dashboard supports two identity providers:

- **Local dashboard accounts**, stored and managed by the application.
- **Proxmox VE accounts**, authenticated by the Proxmox HTTPS ticket API and
  admitted only when an administrator has explicitly mapped the exact
  Proxmox identity to a dashboard role.

The application owns sessions and permissions in both cases. Proxmox
authentication does not grant access by itself, and Proxmox ACLs do not
implicitly become dashboard permissions. Unmapped Proxmox identities are
denied. There is no public registration. The first local administrator is
provisioned from the backend command line; subsequent users, role changes,
password resets, disabling accounts, and Proxmox identity mappings are also
managed through that trusted local CLI.

Windows tests can verify local accounts, session behavior, authorization,
and mocked Proxmox responses. They cannot verify a real Proxmox realm,
certificate, ticket lifetime, disabled-user behavior, reverse-proxy TLS, or
production cookie behavior. Keep the backend bound to loopback until the
deployment security checks below pass.

## Identity and role policy

### Local dashboard accounts

- Usernames are unique, case-insensitive dashboard identities.
- Passwords are never stored in plaintext; local credentials use a salted,
  adaptive password hash. Passwords must be 8-1024 characters long.
- Local account creation is CLI-only; there is no self-registration or public
  password-reset flow. An administrator resets a password using the local
  CLI.
- Account creation and role changes require access to the host running the
  backend and its authentication database.

### Proxmox identities

- Sign in with a Proxmox user ID including its realm, for example `user@pve`.
- Send credentials only to the configured Proxmox API over HTTPS with
  certificate validation enabled. Never disable TLS verification to bypass
  certificate errors.
- Do not store or log the submitted Proxmox password, ticket, or CSRF token.
  The ticket is used only to verify the login; the dashboard creates its own
  application session.
- Administrators explicitly map each exact Proxmox user ID to `admin`,
  `operator`, or `viewer` using the trusted local CLI. Unmapped users are
  denied by default. There is no automatic Proxmox group or ACL-to-role
  translation.
- Use dedicated, non-root Proxmox users for routine access. API tokens are
  separate machine credentials and are not interactive login credentials.

### Dashboard roles

- **Viewer:** read-only system/model/bot status and observe-only diagnostics.
- **Operator:** viewer access plus chat/research, an explicit diagnostics
  observation, and model selection.
- **Admin:** operator access plus backend log access, bot restart, and
  read/manage access to explicitly published shared operational notes. User
  and Proxmox-role administration remains a local CLI operation.

All routes are denied unless public, authenticated with the dedicated
Discord-bot service credential, or authorized for the caller's role. WebSocket
chat requires an authenticated operator session. A browser origin check is
additional protection, not authentication.

## Login and application sessions

- `POST /api/auth/login` accepts a provider (`local` or `proxmox`), username,
  and password. Responses use generic credential errors and create a random,
  opaque server-side session.
- The session identifier is delivered only in an `HttpOnly`, `SameSite`
  cookie, configured `Secure` for HTTPS deployments. Neither session IDs nor
  provider credentials belong in local storage, URLs, or logs.
- The backend stores only a digest of the opaque session identifier, along
  with identity, role, creation/expiry times, and a CSRF secret. Logout
  revokes the server-side session and clears the cookie.
- Sessions have bounded idle and absolute lifetimes. The initial policy is a
  30-minute idle timeout and 12-hour absolute lifetime; sessions are not
  silently extended beyond the absolute lifetime. Reauthenticate after
  expiry. These values must be revisited after real deployment testing.
- `GET /api/auth/status` reports the authenticated identity and role, or
  `authenticated: false`; it does not return the session ID.
- State-changing browser requests require the session CSRF token in
  `X-CSRF-Token` and an allowed `Origin`. Login is origin-checked and
  rate-limited. WebSocket handshakes require both a valid session and an
  allowed dashboard origin.
- Login attempts are throttled per identity and source address. Do not trust
  forwarded client IP headers unless a specifically trusted proxy is later
  configured.

The Discord bot is a machine client, not an interactive dashboard user. Its
backend calls use a separate, high-entropy bearer credential configured
outside source control. This credential is limited to bot API routes and
must not grant dashboard administrator access.

Dashboard conversation history is scoped to the identity provider and
username. The backend does not expose one account's conversations to another;
the bot service credential is not an account and does not create dashboard
history. Conversation history is stored separately from authentication
records in the configured memory database and remains until the owner deletes
it.

Shared admin memory is a separate store of operational notes. An admin must
explicitly publish each note; there is no transcript scraping, automatic
fact-sharing, or model training. Every admin can read and remove published
notes, and admin chat/research context may include the newest bounded set.
Admins are told which identity is signed in, but the model is never given
another admin's private transcript. Non-admin accounts and the Discord bot
service credential cannot access or receive shared admin notes.

## API behavior

- `POST /api/auth/login` — authenticate `local` or `proxmox` credentials and
  set the session cookie. Returns a CSRF token and identity/role metadata.
- `GET /api/auth/status` — return current identity/role and CSRF token, or
  `authenticated: false`.
- `POST /api/auth/logout` — revoke the current session and clear its cookie.
- `GET /` — minimal backend health response; no dashboard information.
- `/api/memory/shared-insights` — admin-only, explicit publication and
  management of shared operational notes.
- `/api/bot/*` routes used by the Discord bot require the bot bearer
  credential. All remaining API routes require a role-appropriate session.

No refresh endpoint extends the absolute session lifetime. Authentication
errors must not expose whether a username exists, whether a Proxmox identity
is mapped, or whether its password alone was valid.

## Browser and deployment requirements

- Keep the API bound to loopback during development. Use HTTPS and a same-site
  dashboard/API origin in LAN or remote deployments.
- `AI_SERVER_AUTH_COOKIE_SECURE` must be enabled for HTTPS deployment. Only
  disable it for isolated local HTTP development; do not expose that
  configuration to a network.
- Configure exact dashboard origins; wildcard CORS is not allowed. Browser
  requests include credentials and must not put them in browser storage.
- Protect every non-public REST route and WebSocket; do not treat CORS or
  Origin validation as a substitute for authentication.
- Protect the authentication database and backups as sensitive data.
- Do not log passwords, session IDs, CSRF tokens, Proxmox tickets, bot bearer
  credentials, or submitted chat text.
- Keep the Discord bot bearer credential separate from local user passwords
  and Proxmox credentials. Rotate it if disclosed.

## Implementation and validation

### Windows development — implemented and tested

- The full backend suite passes 81 tests covering local CLI provisioning and
  password reset, local login, session persistence/expiry/revocation, CSRF,
  login throttling, role authorization, mocked Proxmox ticket login and
  explicit mappings, and authenticated REST/WebSocket behavior.
- The dashboard sign-in/status/logout flow and role-aware controls are wired
  to the protected API.
- Machine routes require a scoped bot credential, passed by the Discord bot.
- `node --check js/app.js` and `git diff --check` pass in the Windows
  development environment.

### Before LAN or remote access

- Configure and verify the intended Proxmox realm, API endpoint, exact user
  mappings, and trusted TLS certificate.
- Verify session lifetime and revocation, behavior when Proxmox users are
  disabled, cookie settings through the deployed HTTPS proxy, trusted-origin
  behavior, and rate limits.
- Confirm unauthorized users cannot access REST or WebSocket endpoints and
  each role receives only its documented capabilities.
- Confirm the auth database and bot credential are stored with appropriate
  host permissions and backups.
- Keep LAN/remote access disabled until these checks pass.

## References

- [Proxmox VE User Management](https://pve.proxmox.com/pve-docs/chapter-pveum.html)
- [Proxmox VE API ticket endpoint](https://pve.proxmox.com/pve-docs/api-viewer/index.html#/access/ticket)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
