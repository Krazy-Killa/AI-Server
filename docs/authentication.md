# Authentication & Session Management

## Overview

This document outlines the planned JWT-based authentication system for the AI-Server. This system will secure all API endpoints and provide a robust session management framework for the dashboard, Discord bot, and future services.

**Status**: Planning Phase (Not Yet Implemented)  
**Target Implementation**: Phase 3 (After GPU Integration)  
**Priority**: High (Security Critical)

---

## Architecture Overview

### Authentication Flow

```
User Login
    ↓
POST /api/auth/login (username, password)
    ↓
Backend validates credentials → generates tokens
    ↓
Response: {
  access_token: "eyJ...",      // 15-min JWT (in response body)
  refresh_token: "eyJ...",     // 7-day JWT (in HttpOnly cookie)
  expires_in: 900,              // seconds
  user: { id, username }
}
    ↓
Frontend stores access_token in memory
Browser auto-stores refresh_token in HttpOnly cookie
    ↓
All subsequent requests include: Authorization: Bearer {access_token}
    ↓
Token Expiration (15 min)
    ↓
Frontend auto-refreshes using refresh_token cookie
    ↓
Logout: POST /api/auth/logout
    ↓
Backend blacklists tokens
Frontend clears memory
Browser clears cookie
```

### Token Strategy

| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| **Access Token** | 15 minutes | Response body → JavaScript memory | API request authentication |
| **Refresh Token** | 7 days | HttpOnly cookie | Obtain new access tokens |

---

## Backend Implementation

### Dependencies

Add to `ai-backend/requirements.txt`:
```
PyJWT>=2.8.0              # JWT token generation and validation
bcrypt>=4.1.0             # Password hashing
python-slowapi>=0.1.8     # Rate limiting
```

### Environment Variables

Add to `.env.example`:
```bash
# JWT Configuration
JWT_SECRET_KEY=generate-with-python-secrets-token-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
# CORS origins reuse the existing AI_SERVER_CORS_ORIGINS setting (already
# implemented in ai-backend/config.py); do not add a second origins variable.
MAX_LOGIN_ATTEMPTS=5
LOGIN_ATTEMPT_WINDOW_MINUTES=5

# Session Management
MAX_CONCURRENT_SESSIONS=3
SESSION_CLEANUP_INTERVAL_HOURS=1
```

### Core Modules

#### `ai-backend/auth.py` (New File)

Key functions to implement:
- `hash_password(password: str) -> str` - Hash with bcrypt (cost=12)
- `verify_password(password: str, hash: str) -> bool` - Verify password
- `create_access_token(user_id, username, expires_delta) -> str` - Generate JWT
- `create_refresh_token(user_id, expires_delta) -> str` - Generate refresh JWT
- `verify_token(token: str) -> TokenPayload` - Decode and validate JWT
- `validate_user_credentials(username, password) -> User | None` - Authenticate
- `blacklist_token(jti: str)` - Add to token blacklist
- `is_token_blacklisted(jti: str) -> bool` - Check if revoked

#### `ai-backend/models.py` (New File)

Pydantic models:
```python
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic

class UserPublic(BaseModel):
    user_id: int
    username: str
    created_at: datetime

class StatusResponse(BaseModel):
    authenticated: bool
    user: UserPublic | None
    expires_at: datetime | None
```

### API Endpoints

**1. `POST /api/auth/login`**
- Accept username and password
- Return access_token, expires_in, user info
- Set refresh_token in HttpOnly cookie
- Rate limit: 5 attempts per 5 minutes per IP

**2. `POST /api/auth/logout`**
- Require Authorization header
- Blacklist token JTI
- Clear refresh_token cookie

**3. `POST /api/auth/refresh`**
- Use refresh_token from cookie
- Return new access_token
- Optional: rotate refresh_token

**4. `GET /api/auth/status`**
- Check if authenticated
- Return user info and expiration time

**5. `POST /api/auth/register` (Future)**
- Create new user account
- Initially disabled (CLI-only)

### Protected Endpoints Pattern

```python
@app.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    current_user: User = Depends(require_auth)
):
    """Protected endpoint"""
    return await run_llm(req.message)
```

Apply `@require_auth` dependency to:
- POST /api/chat
- POST /api/research
- POST /api/model/select
- GET /api/models
- POST /api/bot/logs
- POST /api/bot/restart
- And all other non-public endpoints

Keep public:
- GET / (root)
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- GET /api/auth/status

### Security Features

**Password Hashing:**
- Use bcrypt with cost factor 12
- ~100ms per hash (intentional slowdown)
- Never store plaintext passwords

**JWT Claims:**
```python
{
    "sub": user_id,
    "username": username,
    "exp": expiration_timestamp,
    "iat": issued_at_timestamp,
    "jti": unique_token_id,
    "type": "access"
}
```

**Token Blacklist:**
- In-memory set of invalidated JTIs
- Checked on every request
- For production: use Redis for persistence

**CORS Restriction:** already implemented. `main.py` reads the validated
`AI_SERVER_CORS_ORIGINS` setting through `config.settings`; authentication
adds the `Authorization` header to the allowed headers and does not introduce
a new origins variable.
```python
allow_origins=settings.cors_origins
allow_credentials=True
allow_methods=["GET", "POST"]
```

**Rate Limiting:**
- Use python-slowapi
- 5 login attempts per 5 minutes per IP

**Secure Cookies:**
```python
response.set_cookie(
    key="refresh_token",
    value=token,
    max_age=7 * 24 * 60 * 60,
    secure=True,        # HTTPS only
    httponly=True,      # No JavaScript access
    samesite="Strict"   # CSRF protection
)
```

---

## Frontend Implementation

### Login Page

Add to `index.html`:
```html
<div id="login-container" class="login-panel">
  <div class="login-box">
    <div class="login-header">
      <div class="logo-orb" aria-hidden="true"></div>
      <h1>AI COMMAND INTERFACE</h1>
      <p class="login-subtitle">Sign in to continue</p>
    </div>
    
    <form id="login-form" onsubmit="handleLogin(event)">
      <div class="form-group">
        <label for="username-input">Username</label>
        <input type="text" id="username-input" required>
      </div>
      
      <div class="form-group">
        <label for="password-input">Password</label>
        <input type="password" id="password-input" required>
      </div>
      
      <button type="submit" class="btn btn-login">Sign In</button>
      <div id="login-error" class="error-message" role="alert"></div>
    </form>
  </div>
</div>

<div id="app" style="display: none;">
  <!-- Dashboard (shown after login) -->
</div>
```

### Token Management

Create `js/auth.js`:
- `AuthManager` class to manage tokens in memory
- `handleLogin(event)` - POST to /api/auth/login, store token
- `handleLogout()` - POST to /api/auth/logout, clear token
- `fetchWithAuth(url, options)` - Wrapper that adds Authorization header
- Auto-refresh token 1 minute before expiration
- Handle 401/403 responses by redirecting to login

### Integration

Update `js/app.js`:
- Replace `fetch()` calls with `fetchWithAuth()`
- Add logout button to header
- Initialize with login page visibility check

Add to `index.html` header:
```html
<button id="logout-btn" class="btn-logout" onclick="handleLogout()">Logout</button>
```

---

## User Management

### Initial Setup - Option A: CLI

```bash
python ai-backend/main.py --create-admin
# Prompts for username and password
```

### Initial Setup - Option B: Development Default

For development only, provide demo account:
- Username: `admin`
- Password: `password`

Store hash in code during initialization.

### Initial Setup - Option C: Production

- Disable default accounts
- Require CLI registration only
- No self-service signup (initially)

---

## Testing

### Unit Tests (`ai-backend/tests/test_auth.py`)

- Password hashing and verification
- JWT token generation and validation
- Token expiration handling
- Invalid token rejection
- Credential validation
- Token blacklist functionality

### Integration Tests

- Full login flow
- Invalid credentials
- Token refresh
- Logout invalidates token
- Protected endpoints require token
- Rate limiting on login
- CORS enforcement

---

## Deployment

### Windows Development
Generate the secret instead of copying a fixed value, and keep it in the
gitignored `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
```env
JWT_SECRET_KEY=<generated value>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
AI_SERVER_CORS_ORIGINS=http://127.0.0.1:8001,http://localhost:8001
```

### Linux/Proxmox Production
```env
JWT_SECRET_KEY=<output of: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
AI_SERVER_CORS_ORIGINS=https://your-domain.com
```

**Requirements:**
- HTTPS with valid TLS certificate
- Rate limiting at NGINX level
- Consider Redis for token blacklist
- Comprehensive audit logging

---

## Implementation Phases

### Phase 3.1 (MVP)
- [ ] auth.py module with JWT utilities
- [ ] Login/logout/refresh endpoints
- [ ] Token validation middleware
- [ ] Login page UI
- [ ] Auto-token refresh (JS)
- [ ] Protect core endpoints

### Phase 3.2 (Hardening)
- [ ] Rate limiting
- [ ] Session tracking
- [ ] Audit logging
- [ ] Unit & integration tests
- [ ] Documentation updates

### Phase 4+ (Advanced)
- [ ] User registration
- [ ] 2FA/MFA
- [ ] API key auth
- [ ] LDAP integration
- [ ] OAuth2/OIDC

---

## Security Checklist

- [ ] Passwords hashed with bcrypt (cost=12)
- [ ] JWT tokens HS256 algorithm
- [ ] Short access token lifetime (15 min)
- [ ] Long refresh token lifetime (7 days)
- [ ] Refresh tokens in HttpOnly cookies
- [ ] Access tokens in response body only
- [ ] Token validation on protected endpoints
- [ ] Token blacklist on logout
- [ ] Rate limiting on login
- [ ] CORS restricted to allowed origins
- [ ] Secure cookie flags (HttpOnly, Secure, SameSite)
- [ ] Audit logging of auth events
- [ ] No passwords/tokens in logs
- [ ] Environment variables for secrets
- [ ] HTTPS enforced in production

---

## References

- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [bcrypt Documentation](https://github.com/pyca/bcrypt)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
