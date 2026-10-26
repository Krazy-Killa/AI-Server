from fastapi import Request

from api import runtime


ROUTE_ROLES = {
    ("GET", "/api/system"): "viewer",
    ("GET", "/api/gpu"): "viewer",
    ("GET", "/api/backend/logs"): "admin",
    ("GET", "/api/diagnostics/status"): "viewer",
    ("GET", "/api/diagnostics/observations"): "viewer",
    ("GET", "/api/diagnostics/incidents"): "viewer",
    ("GET", "/api/diagnostics/report"): "viewer",
    ("GET", "/api/diagnostics/runbooks"): "viewer",
    ("GET", "/api/diagnostics/runbook"): "viewer",
    ("GET", "/api/diagnostics/knowledge/search"): "viewer",
    ("GET", "/api/bot/status"): "viewer",
    ("GET", "/api/bot/logs"): "admin",
    ("GET", "/api/models"): "viewer",
    ("GET", "/api/proxmox/vms"): "viewer",
    ("GET", "/api/vision"): "viewer",
    ("POST", "/api/chat"): "operator",
    ("POST", "/api/research"): "operator",
    ("POST", "/api/research/stream"): "operator",
    ("GET", "/api/interface/conversation"): "admin",
    ("POST", "/api/interface/chat"): "admin",
    ("GET", "/api/memory/conversations"): "operator",
    ("POST", "/api/memory/conversations"): "operator",
    ("GET", "/api/memory/shared-insights"): "admin",
    ("POST", "/api/memory/shared-insights"): "admin",
    ("DELETE", "/api/memory/shared-insights/{insight_id}"): "admin",
    ("POST", "/api/diagnostics/observe"): "operator",
    ("POST", "/api/bot/restart"): "admin",
    ("POST", "/api/model/select"): "operator",
    ("POST", "/api/embed"): "operator",
    ("POST", "/api/llm"): "operator",
    ("POST", "/api/vision/run"): "operator",
}

BOT_API_ROUTES = {
    ("POST", "/api/chat"),
    ("GET", "/api/models"),
    ("POST", "/api/model/select"),
    ("GET", "/api/bot/status"),
    ("POST", "/api/bot/heartbeat"),
    ("POST", "/api/bot/logs"),
    ("POST", "/api/embed"),
}

BOT_ONLY_ROUTES = {
    ("POST", "/api/bot/heartbeat"),
    ("POST", "/api/bot/logs"),
}

async def authenticate_http_requests(request: runtime.Request, call_next):
    path = request.url.path
    method = request.method.upper()
    if method == "OPTIONS" or path == "/" or path == "/api/auth/status":
        return await call_next(request)
    if path == "/api/auth/login":
        if not runtime._origin_allowed(request.headers.get("origin")):
            return runtime._json_error(403, "Login request origin is not allowed.")
        return await call_next(request)
    if not path.startswith("/api/"):
        return await call_next(request)

    authorization = request.headers.get("authorization", "")
    if authorization:
        scheme, _, credential = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not runtime.settings.bot_api_token:
            return runtime._json_error(401, "Invalid service credential.")
        if not runtime.hmac.compare_digest(credential, runtime.settings.bot_api_token):
            return runtime._json_error(401, "Invalid service credential.")
        if (method, path) not in BOT_API_ROUTES:
            return runtime._json_error(403, "Service credential is not authorized for this route.")
        request.state.service_identity = "discord-bot"
        return await call_next(request)

    if (method, path) in BOT_ONLY_ROUTES:
        return runtime._json_error(401, "Service authentication is required.")

    token = request.cookies.get("ai_server_session")
    session = runtime.get_auth_store().get_session(
        token, touch=method not in ("GET", "HEAD")
    )
    if session is None:
        return runtime._json_error(401, "Authentication is required.")
    request.state.auth_session = session
    if path == "/api/auth/logout":
        required_role = "viewer"
    else:
        required_role = ROUTE_ROLES.get((method, path))
        if (
            required_role is None
            and path.startswith("/api/memory/conversations/")
            and "/" not in path[len("/api/memory/conversations/"):]
            and method in {"GET", "DELETE"}
        ):
            required_role = "operator"
        if (
            required_role is None
            and path.startswith("/api/memory/shared-insights/")
            and "/" not in path[len("/api/memory/shared-insights/"):]
            and method == "DELETE"
        ):
            required_role = "admin"
        if (
            required_role is None
            and path.startswith("/api/diagnostics/runbooks/")
            and "/" not in path[len("/api/diagnostics/runbooks/"):]
            and method == "GET"
        ):
            required_role = "viewer"
        if required_role is None:
            return runtime._json_error(403, "This route is not enabled for dashboard sessions.")
    if not runtime._role_allows(session.role, required_role):
        return runtime._json_error(403, "This account is not authorized for this action.")

    if method not in ("GET", "HEAD"):
        if not runtime._origin_allowed(request.headers.get("origin")):
            return runtime._json_error(403, "Request origin is not allowed.")
        csrf_token = request.headers.get("x-csrf-token", "")
        if not runtime.hmac.compare_digest(csrf_token, session.csrf_token):
            return runtime._json_error(403, "CSRF validation failed.")
    result = await call_next(request)
    if method not in ("GET", "HEAD") and path != "/api/auth/logout" and result.status_code < 400:
        result.set_cookie(
            "ai_server_session",
            token,
            max_age=max(1, session.expires_at - int(runtime.time.time())),
            httponly=True,
            secure=runtime.settings.auth_cookie_secure,
            samesite="strict",
            path="/",
        )
    return result

async def log_requests(request: runtime.Request, call_next):
    started_at = runtime.monotonic()
    level = (
        runtime.logging.DEBUG
        if request.url.path in runtime.QUIET_PATHS
        else runtime.logging.INFO
    )
    try:
        response = await call_next(request)
    except Exception:
        runtime.logger.exception("%s %s failed", request.method, request.url.path)
        raise
    runtime.logger.log(
        level,
        "%s %s -> %d (%d ms)",
        request.method,
        request.url.path,
        response.status_code,
        round((runtime.monotonic() - started_at) * 1000),
    )
    return response


def register_middleware(app):
    app.middleware("http")(authenticate_http_requests)
    app.middleware("http")(log_requests)
    app.add_middleware(
        runtime.CORSMiddleware,
        allow_origins=list(runtime.settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
