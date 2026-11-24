"""Middleware de segurança do backend (camada 2): headers, rate limit e limite de tamanho."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .audit_logger import log_event
from .config import security_config as cfg
from .rate_limiter import rate_limiter

_LLM_PATHS = ("/api/classify", "/api/upload-csv")
_NO_CSP_PATHS = ("/docs", "/redoc", "/openapi.json")

_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _block(status: int, message: str, event: str, request: Request, **extra) -> JSONResponse:
    log_event(event, "backend", ip=client_ip(request), path=request.url.path, **extra)
    return JSONResponse(status_code=status, content={"detail": message})


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not cfg.layer(cfg.backend_enabled):
            return await call_next(request)

        path, ip = request.url.path, client_ip(request)

        if cfg.rate_limit_enabled and path.startswith("/api/"):
            limited = not rate_limiter.allow(f"{ip}:all", cfg.rate_limit_per_minute)
            if not limited and path in _LLM_PATHS:
                limited = not rate_limiter.allow(f"{ip}:llm", cfg.rate_limit_llm_per_minute)
            if limited:
                resp = _block(429, "Muitas requisições. Tente novamente em instantes.", "RATE_LIMITED", request)
                resp.headers["Retry-After"] = "60"
                return resp

        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > cfg.max_request_bytes:
            return _block(413, "Requisição muito grande.", "REQUEST_TOO_LARGE", request, size=int(length))

        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if not path.startswith(_NO_CSP_PATHS):
            response.headers["Content-Security-Policy"] = _CSP
        return response
