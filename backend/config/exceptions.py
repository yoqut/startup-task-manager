"""
Global exception handler — returns consistent JSON error responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "success": False,
            "error": {
                "code": response.status_code,
                "message": _extract_message(response.data),
                "detail": response.data,
            },
        }
        response.data = error_payload
    else:
        logger.exception("Unhandled exception in view: %s", context.get("view"))
        response = Response(
            {
                "success": False,
                "error": {
                    "code": 500,
                    "message": "An unexpected error occurred.",
                    "detail": str(exc),
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message(data):
    if isinstance(data, dict):
        for key in ("detail", "message", "non_field_errors"):
            if key in data:
                val = data[key]
                return str(val[0]) if isinstance(val, list) else str(val)
        first_val = next(iter(data.values()), "")
        return str(first_val[0]) if isinstance(first_val, list) else str(first_val)
    if isinstance(data, list):
        return str(data[0])
    return str(data)
