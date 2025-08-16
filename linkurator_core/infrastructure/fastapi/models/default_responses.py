import http

from fastapi import HTTPException, Response, status


def not_authenticated() -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.UNAUTHORIZED,
        detail="Not authenticated")


def forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.FORBIDDEN,
        detail=message)


def bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.BAD_REQUEST,
        detail=message)


def not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.NOT_FOUND,
        detail=message)


def too_many_requests(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
        detail=message)


def rate_limit_exceeded(message: str) -> HTTPException:
    return HTTPException(
        status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
        detail=message,
    )


class EmptyResponse(Response):
    """
    A custom response class that represents an empty response with a 204 No Content status code.
    This is used when no content needs to be returned in the response body.
    """

    media_type = None

    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_204_NO_CONTENT)
