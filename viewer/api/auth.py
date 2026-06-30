from __future__ import annotations

import base64
import binascii
import secrets

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

_REALM = "Articraft Viewer"
_PUBLIC_PATHS = frozenset({"/health"})


class BasicAuthMiddleware:
    """Gate every HTTP request behind a single HTTP Basic credential pair."""

    def __init__(self, app: ASGIApp, *, username: str, password: str) -> None:
        self._app = app
        self._username = username
        self._password = password

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request = Request(scope)
        if request.method == "OPTIONS" or request.url.path in _PUBLIC_PATHS:
            await self._app(scope, receive, send)
            return

        if self._is_authorized(request.headers.get("authorization")):
            await self._app(scope, receive, send)
            return

        response = Response(
            status_code=401,
            headers={"WWW-Authenticate": f'Basic realm="{_REALM}", charset="UTF-8"'},
        )
        await response(scope, receive, send)

    def _is_authorized(self, header: str | None) -> bool:
        if not header:
            return False
        scheme, _, encoded = header.partition(" ")
        if scheme.lower() != "basic" or not encoded:
            return False
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return False
        username, separator, password = decoded.partition(":")
        if not separator:
            return False
        valid_username = secrets.compare_digest(username, self._username)
        valid_password = secrets.compare_digest(password, self._password)
        return valid_username and valid_password
