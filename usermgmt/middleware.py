from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .drf_auth import JWTAuthentication


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.erp_user = None
        request.jwt_payload = None

        auth = JWTAuthentication()
        header = auth.get_header(request)
        if header is None:
            return None

        try:
            raw_token = auth.get_raw_token(header)
            if raw_token is None:
                return None
            validated_token = auth.get_validated_token(raw_token)
            user = auth.get_user(validated_token)
        except (InvalidToken, TokenError):
            return None

        request.erp_user = user
        request.jwt_payload = dict(validated_token.payload)
        return None
