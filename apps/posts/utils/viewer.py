# import hashlib
import uuid

from rest_framework.request import Request


def get_viewer_id(request: Request):
    """
    Returns a stable unique viewer identifier for:
    - authenticated users
    - mobile apps using device-id header
    - browsers via cookie
    - fallback: hashed IP + user-agent
    """
    if request.user.is_authenticated:
        return f"user:{request.user.pk}", None

    device_id = request.META.get("X-Device-ID")
    if device_id:
        return f"device:{device_id}", None

    viewer_cookie = request.COOKIES.get("viewer_id")
    cookie_to_set = None
    if viewer_cookie:
        return f"cookie:{viewer_cookie}", None
    else:
        new_cookie = str(uuid.uuid4())
        cookie_to_set = new_cookie
        return f"cookie:{new_cookie}", cookie_to_set
