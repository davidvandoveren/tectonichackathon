"""Caps the size of request bodies before anything parses them.

Without a cap a single request with a huge JSON body is read into memory in full before pydantic
ever gets to check `max_length` (resource exhaustion, CWE-400). The check covers both a declared
`Content-Length` and chunked uploads that do not declare one.
"""

from collections.abc import Mapping

from fastapi import HTTPException, status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_MAX_BODY_BYTES = 64 * 1024
# Speech-to-text uploads carry up to ~2 MiB of audio, base64 encoded (+33%).
MAX_BODY_BYTES_BY_PATH: Mapping[str, int] = {"/api/v1/kate/transcribe": 3 * 1024 * 1024}

_TOO_LARGE = "Request body too large"


class BodySizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = DEFAULT_MAX_BODY_BYTES,
        limits_by_path: Mapping[str, int] = MAX_BODY_BYTES_BY_PATH,
    ) -> None:
        self.app = app
        self._default = default_limit
        self._by_path = limits_by_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self._by_path.get(scope["path"], self._default)

        declared = _content_length(scope)
        if declared is not None and declared > limit:
            await JSONResponse({"detail": _TOO_LARGE}, 413)(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Stops reading right here. Usually a 413; when the exception travels through
                    # Starlette's BaseHTTPMiddleware task group FastAPI reports it as a 400.
                    # Either way the request is refused and never buffered in full.
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, _TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope["headers"]:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
