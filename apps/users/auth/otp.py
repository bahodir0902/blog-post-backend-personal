import secrets
import uuid
from dataclasses import dataclass
from typing import Optional

from decouple import config
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache

try:
    from django_redis import get_redis_connection  # type: ignore
except Exception:
    get_redis_connection = None  # not on django-redis backend

OTP_LEN = config("OTP_LEN", cast=int, default=6)
TTL_SECONDS = config("TTL_SECONDS", cast=int, default=300)
MAX_ATTEMPTS = config("MAX_ATTEMPTS", cast=int, default=5)

DEFAULT_SCOPE = "mfa"  # keep old behavior for login serializer


def _key(scope: str, token: str) -> str:
    return f"otp:{scope}:{token}"


def _set(key: str, value: dict, ttl: Optional[int] = None) -> None:
    cache.set(key, value, ttl if ttl is not None else TTL_SECONDS)


def _touch_preserving_ttl(key: str, value: dict) -> None:
    # 1) Best path: Redis SET with KEEPTTL (atomic, preserves expiry)
    try:
        if get_redis_connection and cache.__class__.__module__.startswith("django_redis"):
            # Build the real cache key + serialize exactly like the cache backend
            real_key = cache.make_key(key, version=getattr(cache, "version", None))
            client = get_redis_connection("default")
            serializer = cache.client.get_serializer()  # django-redis API for serializer
            client.set(real_key, serializer.dumps(value), keepttl=True)
            return
    except Exception:
        # fall through to best-effort fallback
        pass

    try:
        ttl = getattr(cache, "ttl", None)
        if callable(ttl):
            remaining = cache.ttl(key)  # returns seconds; 0/None/-1 mean special cases
            if isinstance(remaining, int) and remaining > 0:
                cache.set(key, value, remaining)
                return
    except Exception:
        pass

    # 3) Last resort: reset to full TTL (current behavior)
    cache.set(key, value, TTL_SECONDS)


@dataclass
class VerifyResult:
    ok: bool
    expired_or_exceeded: bool
    uid: Optional[int]
    meta: dict


def create_scoped_otp(*, scope, uid, meta, ttl=TTL_SECONDS) -> tuple[str, str]:
    """
    Returns (token, code). Store hashed code + attempts in cache.
    """
    code = f"{secrets.randbelow(10 ** OTP_LEN):0{OTP_LEN}d}"
    token = str(uuid.uuid4())
    _set(
        _key(scope, token),
        {"uid": uid, "meta": meta or {}, "code": make_password(code), "attempts": 0},
        ttl,
    )
    return token, code


def create_otp_code(
    user_id: Optional[int] = None, *, scope: str = DEFAULT_SCOPE, meta: Optional[dict] = None
) -> tuple[str, str]:
    return create_scoped_otp(scope=scope, uid=user_id, meta=meta)


def verify_scoped_otp(scope: str, token: str, code: str, *, consume: bool = True) -> VerifyResult:
    key = _key(scope, token)
    data: Optional[dict] = cache.get(key)
    if not data:
        return VerifyResult(ok=False, expired_or_exceeded=True, uid=None, meta={})

    attempts = int(data.get("attempts", 0))
    if attempts >= MAX_ATTEMPTS:
        cache.delete(key)
        return VerifyResult(ok=False, expired_or_exceeded=True, uid=None, meta={})

    if not check_password(code, data["code"]):
        data["attempts"] = attempts + 1
        _touch_preserving_ttl(key, data)
        # still not expired, but invalid try
        return VerifyResult(
            ok=False, expired_or_exceeded=False, uid=data.get("uid"), meta=data.get("meta", {})
        )

    # success
    if consume:
        cache.delete(key)
    return VerifyResult(
        ok=True, expired_or_exceeded=False, uid=data.get("uid"), meta=data.get("meta", {})
    )


# Backward-compatible verify used by your login serializer (scope defaults to "mfa").
# Returns uid, or None (expired/exceeded), or False (invalid).
def verify(token: str, code: str, *, scope: str = DEFAULT_SCOPE) -> Optional[int] | bool:
    res = verify_scoped_otp(scope, token, code, consume=True)
    if res.ok:
        return res.uid
    if res.expired_or_exceeded:
        return None
    return False
