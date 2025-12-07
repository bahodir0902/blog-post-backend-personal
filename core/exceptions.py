import logging
import traceback

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that logs all exceptions.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the exception
    view = context.get("view")
    request = context.get("request")
    user_id = None
    if request and hasattr(request, "user") and request.user.is_authenticated:
        user_id = request.user.pk

    # Get exception details
    exc_type = type(exc).__name__
    exc_message = str(exc) if exc else "Unknown error"
    view_name = view.__class__.__name__ if view else "Unknown"
    path = request.path if request else "Unknown"

    # Build log message
    log_message = f"[EXCEPTION] {exc_type} in {view_name} at {path} - {exc_message}"
    if user_id:
        log_message += f" - user_id={user_id}"

    # Get full traceback
    try:
        exc_traceback = traceback.format_exc()
    except Exception:
        exc_traceback = "Unable to get traceback"

    # Log based on response status
    if response is not None:
        status_code = response.status_code
        if status_code >= 500:
            logger.error(f"{log_message}\nTraceback:\n{exc_traceback}")
        elif status_code >= 400:
            logger.warning(f"{log_message}\nTraceback:\n{exc_traceback}")
    else:
        # Unhandled exception (500)
        logger.error(f"{log_message}\nTraceback:\n{exc_traceback}")

    return response
