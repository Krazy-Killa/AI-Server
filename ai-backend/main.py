"""FastAPI application assembly and compatibility exports."""

from fastapi import FastAPI

from api import runtime
from config import settings
from api.middleware import register_middleware
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.memory import router as memory_router
from api.routes.operations import router as operations_router
from api.routes.research import router as research_router

def create_app(enable_api_docs: bool) -> FastAPI:
    # The interactive docs and schema describe the full API surface to anonymous
    # callers, so they are exposed only when explicitly enabled for development.
    if enable_api_docs:
        return FastAPI()
    return FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


app = create_app(settings.enable_api_docs)
register_middleware(app)
for router in (auth_router, memory_router, chat_router, research_router, operations_router):
    app.include_router(router)
