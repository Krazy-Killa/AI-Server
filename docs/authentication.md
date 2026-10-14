# Authentication & Session Management

## Status and scope

**Status:** Design complete; not implemented.
**Production implementation and validation:** Waiting for the Proxmox server.

The AI Server will authenticate dashboard users against Proxmox VE rather than
maintaining a second username/password database. The backend will still own
application sessions and authorization: successful Proxmox authentication
identifies the user, but does not by itself grant access to AI Server features.

The Windows test environment has no Proxmox identity provider. Work that can
be done before the server exists is limited to interface design, isolated
components, and mocked tests. The real login flow, session lifetime and
revocation behavior must be implemented and validated against the target
Proxmox VE host before enabling LAN or remote access.

## Authentication design

### Proxmox identity

- Users sign in with a Proxmox VE user ID, including its realm, such as
  `user@pve`, `user@pam`, or an organization-configured LDAP/OIDC realm.
- The backend sends the submitted credentials to the configured Proxmox API
  over HTTPS and validates the TLS certificate.
- The backend does not store or log the user's Proxmox password.
- Use a dedicated, non-root Proxmox account for routine dashboard access.
  Never ask users to sign in as `root`.
- Proxmox API tokens are for narrowly scoped server-to-server automation, not
  for interactive dashboard login. Keep any such token separate from user
  sessions and grant only the permissions that integration requires.

### Login and application session flow

1. The browser submits the Proxmox user ID and password to
   `POST /api/auth/login` over HTTPS.
2. The backend calls the Proxmox VE ticket endpoint
   `POST /api2/json/access/ticket` and checks the response.
3. On success, the backend creates an application session associated with the
   authenticated Proxmox user and realm. The application session is distinct
   from the Proxmox ticket.
4. The backend returns a random, opaque session identifier in a `Secure`,
   `HttpOnly`, `SameSite` cookie. Do not return the Proxmox ticket to browser
   JavaScript or put it in local storage.
5. The backend stores session state server-side, including the Proxmox
   identity, creation/expiry times, and revocation state. Mutating requests
   must have CSRF protection and pass origin checks.
6. Logout revokes the application session and clears the cookie. The backend
   must not claim to log the user out of the Proxmox web interface.

The exact application-session lifetime, Proxmox ticket handling/renewal, and
behavior when an account is disabled must be settled and tested against the
installed Proxmox VE version. Sessions must have bounded lifetimes and be
revocable; do not use a self-contained JWT as the only session state if that
would prevent prompt revocation.

## Application authorization

Proxmox authentication proves identity. It does not automatically authorize
dashboard actions or make Proxmox ACLs equivalent to AI Server permissions.
The AI Server must:

- Map Proxmox identities or approved Proxmox groups to explicit application
  roles and capabilities.
- Deny access by default and protect every non-public API and WebSocket.
- Keep application permissions separate from any service API token used to
  manage Proxmox resources.
- Audit successful and failed logins, session creation/revocation, and
  privileged application actions without recording passwords or tokens.

Initially, access should be restricted to a configured allowlist of Proxmox
users or groups. The policy for mapping Proxmox users/groups to dashboard
roles must be finalized before implementation.

## Proposed application endpoints

- `POST /api/auth/login` — authenticate against Proxmox and set the session
  cookie.
- `POST /api/auth/logout` — revoke the current application session and clear
  its cookie.
- `GET /api/auth/status` — return the current application identity and
  capabilities, or an unauthenticated response.
- `POST /api/auth/refresh` — renew or revalidate the application session only
  according to the behavior verified for the target Proxmox version. Do not
  extend a session beyond its permitted Proxmox-backed lifetime.

Registration, local password reset, password hashing, and AI Server-managed
user accounts are out of scope. User and credential lifecycle remains with
Proxmox and its configured authentication realm.

## Browser and API security requirements

- Serve the dashboard and API over HTTPS in any LAN or remote deployment.
- Use a same-origin reverse proxy where practical.
- Set session cookies with `Secure`, `HttpOnly`, and `SameSite`; use a CSRF
  token or equivalent protection for state-changing cookie-authenticated
  requests.
- Restrict CORS and WebSocket origins to configured dashboard origins.
- Rate-limit login attempts and return generic credential failure messages.
- Never log passwords, Proxmox tickets, application session IDs, or API tokens.
- Keep sessions and Proxmox credentials out of URL parameters and browser
  storage.
- Validate Proxmox's TLS certificate; do not disable certificate verification
  to work around deployment issues.

## Implementation and validation plan

### Before the Proxmox server exists

- Define the Proxmox API client and application authorization interfaces.
- Write unit tests with a mocked Proxmox ticket endpoint.
- Prepare the login UI and unauthenticated/authorized frontend states.
- Do not present mocked authentication as production-ready authentication.

### On the Proxmox server

- Configure and verify the intended Proxmox realm, user/group allowlist, API
  endpoint, and HTTPS certificate.
- Implement and test the Proxmox login integration and application session
  store.
- Verify expiration, renewal/revalidation, logout/revocation, disabled-user
  behavior, CSRF protections, origin restrictions, and rate limits.
- Test that unauthorized users cannot access protected HTTP or WebSocket
  endpoints and that application roles do not grant unintended Proxmox
  privileges.
- Enable LAN or remote access only after the security checks pass.

## References

- [Proxmox VE User Management](https://pve.proxmox.com/pve-docs/chapter-pveum.html)
- [Proxmox VE API ticket endpoint](https://pve.proxmox.com/pve-docs/api-viewer/index.html#/access/ticket)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
