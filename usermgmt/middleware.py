from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import AuthenticationFailed

from .drf_auth import JWTAuthentication


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.erp_user = None
        request.jwt_payload = None

        auth = JWTAuthentication()
        try:
            authenticated = auth.authenticate(request)
        except AuthenticationFailed:
            return None
        if authenticated is None:
            return None

        user, validated_token = authenticated

        request.erp_user = user
        request.jwt_payload = dict(validated_token.payload)
        return None
