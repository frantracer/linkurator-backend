import http

from fastapi import HTTPException


def not_authenticated() -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.UNAUTHORIZED,
        detail="Not authenticated")


def bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.BAD_REQUEST,
        detail=message)


def not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.NOT_FOUND,
        detail=message)
