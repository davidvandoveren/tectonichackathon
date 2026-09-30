import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.domain.bank import Bank
from app.domain.seed import seed_bank
from app.routers import auth, banking, subscriptions
from app.security.headers import CsrfGuardMiddleware, SecurityHeadersMiddleware
from app.security.rate_limit import FailureLimiter
from app.security.sessions import SessionStore
from app.subscriptions.scenario import book_subscriptions
from app.subscriptions.store import FeedbackStore

logger = logging.getLogger("kbc_poc")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        bank = Bank()
        seed_bank(bank, settings.demo_password.get_secret_value(), date.today())
        book_subscriptions(bank, date.today())
        app.state.subscription_feedback = FeedbackStore()
        app.state.bank = bank
        app.state.sessions = SessionStore(settings.session_ttl_seconds)
        app.state.login_limiter = FailureLimiter(
            settings.login_max_failures, settings.login_window_seconds
        )
        logger.info(
            "Seeded %d synthetic customers (env=%s)", len(bank.list_users()), settings.app_env
        )
        yield

    app = FastAPI(
        title="KBC Mobile PoC API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs only outside production: less attack surface for judges' scanners.
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.add_middleware(CsrfGuardMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo submitted values (they can contain passwords); only say what was wrong.
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ())[1:]) or "request"
        message = str(first.get("msg", "Invalid request")).removeprefix("Value error, ")
        return JSONResponse(
            {"detail": f"{field}: {message}"}, status.HTTP_422_UNPROCESSABLE_CONTENT
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(banking.router, prefix="/api/v1")
    app.include_router(subscriptions.router, prefix="/api/v1")

    if settings.static_dir and (settings.static_dir / "index.html").is_file():
        _mount_frontend(app, settings.static_dir.resolve())
    return app


def _mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve the built SPA from the same origin; unknown paths fall back to index.html."""
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    index = static_dir / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static_dir):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
