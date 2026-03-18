from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .auth import JWTError, decode_jwt
from .models import User
from .services import is_token_blacklisted


class JWTAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].lower() != self.keyword:
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Invalid Authorization header")

        token = auth[1].decode("utf-8")
        try:
            payload = decode_jwt(token)
        except JWTError as exc:
            raise AuthenticationFailed(str(exc)) from exc

        if is_token_blacklisted(payload.get("jti", "")):
            raise AuthenticationFailed("Token is blacklisted")

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed("Invalid token payload")

        try:
            user = User.objects.select_related("role").get(id=user_id, is_active=True)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("User not found or inactive") from exc

        request.jwt_payload = payload
        return (user, payload)
