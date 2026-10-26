"""FastAPI application assembly and compatibility exports."""

from fastapi import FastAPI

from api import runtime
from api.middleware import register_middleware
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.memory import router as memory_router
from api.routes.operations import router as operations_router
from api.routes.research import router as research_router

app = FastAPI()
register_middleware(app)
for router in (auth_router, memory_router, chat_router, research_router, operations_router):
    app.include_router(router)
