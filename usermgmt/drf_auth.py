from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .services import is_token_blacklisted


class JWTAuthentication(SimpleJWTAuthentication):
    def authenticate(self, request):
        try:
            authenticated = super().authenticate(request)
        except (InvalidToken, TokenError) as exc:
            raise AuthenticationFailed(str(exc)) from exc

        if authenticated is None:
            return None

        user, validated_token = authenticated
        jti = validated_token.get("jti")
        if jti and is_token_blacklisted(jti):
            raise AuthenticationFailed("Token is blacklisted")

        request.jwt_payload = dict(validated_token.payload)
        return (user, validated_token)
