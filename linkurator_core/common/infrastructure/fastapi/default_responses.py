import http

from fastapi.responses import JSONResponse


def not_authenticated() -> JSONResponse:
    return JSONResponse(
        status_code=http.HTTPStatus.UNAUTHORIZED,
        content={"detail": "Not authenticated"})
