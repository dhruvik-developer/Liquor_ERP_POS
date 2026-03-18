import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings


class JWTError(Exception):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(digest)


def encode_jwt(payload: dict, expires_in_minutes: int = 60) -> str:
    secret = settings.SECRET_KEY
    now = datetime.now(timezone.utc)
    full_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        "jti": secrets.token_hex(16),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(full_payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(f"{header_b64}.{payload_b64}".encode("utf-8"), secret)
    return f"{header_b64}.{payload_b64}.{signature}"


def decode_jwt(token: str) -> dict:
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError as exc:
        raise JWTError("Invalid token format") from exc

    secret = settings.SECRET_KEY
    signed = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = _sign(signed, secret)

    if not hmac.compare_digest(signature, expected):
        raise JWTError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise JWTError("Invalid payload") from exc

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if payload.get("exp") is None or payload["exp"] < now_ts:
        raise JWTError("Token expired")

    return payload
