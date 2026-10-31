from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter
from app.core.settings import get_settings
from app.routers import admin, assistant, auth, catalog, dashboard, files, health, meta, projects, redesigns

FIELD_LABELS = {
    "full_name": "nombre",
    "email": "correo",
    "password": "contraseña",
    "role": "tipo de cuenta",
    "image": "foto",
    "room_type": "tipo de habitación",
    "style": "estilo",
    "budget": "presupuesto",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().seed_on_startup:
        from app.seed import run_seed

        run_seed()
    yield


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = sorted({FIELD_LABELS.get(str(error["loc"][-1]), str(error["loc"][-1])) for error in exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": f"Revisa estos datos: {', '.join(fields)}", "fields": fields},
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    response = _rate_limit_exceeded_handler(request, exc)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Demasiados intentos seguidos. Espera un momento e inténtalo de nuevo"},
        headers=dict(response.headers),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        redoc_url=None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    routers = (health, auth, catalog, dashboard, projects, redesigns, assistant, admin, meta, files)
    for router in (module.router for module in routers):
        app.include_router(router, prefix=settings.api_prefix)

    if settings.storage_provider == "local":
        media = Path(settings.media_dir)
        media.mkdir(parents=True, exist_ok=True)
        app.mount(settings.media_url_path, StaticFiles(directory=media), name="media")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(f"{settings.api_prefix}/hello")

    return app


app = create_app()
