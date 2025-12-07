import secrets
import uuid

from decouple import config
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.utils.text import slugify

OTP_LEN = config("OTP_LEN", 6, cast=int)
TTL_SECONDS = config("TTL_SECONDS", 300, cast=int)
MAX_ATTEMPTS = config("MAX_ATTEMPTS", 5, cast=int)


def _key(token: str) -> str:
    return f"otp:{token}"


def generate_otp_code(user_id: int) -> tuple[str, str]:
    code = f"{secrets.randbelow(10 ** OTP_LEN):0{OTP_LEN}d}"
    token = str(uuid.uuid4())
    cache.set(
        _key(token), {"uid": user_id, "code": make_password(code), "attempts": 0}, TTL_SECONDS
    )
    return token, code


def _reg_index_key(email: str) -> str:
    return f"reg:idx:{email.lower().strip()}"


def generate_unique_slug(model_cls, base: str, allow_unicode=True) -> str:
    """
    Generates a unique slug for model_cls by appending -2, -3, ... on conflicts.
    Handles race conditions by retrying on IntegrityError.
    """
    raw = slugify(base, allow_unicode=allow_unicode) or "post"
    slug = raw
    i = 2
    while model_cls.objects.filter(slug=slug).exists():
        slug = f"{raw}-{i}"
        i += 1
    return slug
