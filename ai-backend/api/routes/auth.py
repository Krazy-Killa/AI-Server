from fastapi import APIRouter

from api import runtime

router = APIRouter()


@router.post("/api/auth/login")
def auth_login(
    req: runtime.AuthLoginRequest, request: runtime.Request, response: runtime.Response
):
    store = runtime.get_auth_store()
    client_host = request.client.host if request.client else "unknown"
    if store.is_rate_limited(req.username, client_host):
        raise runtime.HTTPException(
            status_code=429, detail="Too many login attempts. Try again later."
        )

    identity: tuple[str, str] | None = None
    if req.provider == "local":
        identity = store.authenticate_local(req.username, req.password)
    else:
        if runtime.proxmox_authenticator is None:
            raise runtime.HTTPException(status_code=503, detail="Proxmox login is not configured.")
        try:
            ticket = runtime.proxmox_authenticator.authenticate(req.username, req.password)
        except runtime.ProxmoxAuthenticationError:
            identity = None
        except runtime.ProxmoxServiceError as error:
            runtime.logger.warning("Proxmox authentication service unavailable: %s", error)
            raise runtime.HTTPException(
                status_code=503, detail="Proxmox authentication service is unavailable."
            ) from error
        else:
            identity = store.authenticate_proxmox(ticket.username)

    if identity is None:
        store.record_failed_login(req.username, client_host)
        raise runtime.HTTPException(
            status_code=401, detail="Invalid credentials or account access."
        )

    username, role = identity
    store.clear_login_failures(req.username, client_host)
    session = store.create_session(req.provider, username, role)
    response.set_cookie(
        "ai_server_session",
        session.token,
        max_age=max(1, session.expires_at - int(runtime.time.time())),
        httponly=True,
        secure=runtime.settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    runtime.logger.info("Dashboard login succeeded (provider=%s, role=%s).", req.provider, role)
    return {
        "authenticated": True,
        "provider": req.provider,
        "username": username,
        "role": role,
        "csrf_token": session.csrf_token,
    }

@router.get("/api/auth/status")
def auth_status(request: runtime.Request, response: runtime.Response):
    session = runtime.get_auth_store().get_session(
        request.cookies.get("ai_server_session"), touch=False
    )
    if session is None:
        response.delete_cookie(
            "ai_server_session",
            path="/",
            secure=runtime.settings.auth_cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return {"authenticated": False}
    return {
        "authenticated": True,
        "provider": session.provider,
        "username": session.username,
        "role": session.role,
        "csrf_token": session.csrf_token,
    }

@router.post("/api/auth/logout")
def auth_logout(request: runtime.Request, response: runtime.Response):
    runtime.get_auth_store().revoke_session(request.cookies.get("ai_server_session"))
    response.delete_cookie(
        "ai_server_session",
        path="/",
        secure=runtime.settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return {"authenticated": False}
