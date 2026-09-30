from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "media-src 'self' blob:",  # Kate's voice is played from an in-memory blob
        "connect-src 'self'",
        "object-src 'none'",
        "frame-src 'none'",
        "worker-src 'self'",
        "manifest-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": _CSP,
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(self), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    # A bank look-alike prototype must never show up in search results (anti-phishing, and it
    # holds only synthetic data anyway).
    "X-Robots-Tag": "noindex, nofollow",
}

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


class CsrfGuardMiddleware(BaseHTTPMiddleware):
    """Defence in depth next to SameSite=Strict cookies.

    State-changing API calls must be JSON (HTML forms cannot send that cross-site without a CORS
    preflight, which we never grant) and, when the browser sends an Origin, it must be our own.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _UNSAFE_METHODS and request.url.path.startswith("/api/"):
            content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                return JSONResponse({"detail": "Content-Type must be application/json"}, 415)
            origin = request.headers.get("origin")
            if origin is not None and origin != _own_origin(request):
                return JSONResponse({"detail": "Cross-origin request blocked"}, 403)
        return await call_next(request)


def _own_origin(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.netloc)
    return f"{scheme}://{host}"
