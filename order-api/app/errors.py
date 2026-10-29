from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base exception for expected, client-facing API errors."""

    status_code = 400

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code or self.status_code
        self.details = details

    def to_dict(self) -> dict:
        payload = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({"error": error.description, "code": error.code}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if app.debug or app.testing:
            raise error
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Internal server error"}), 500
