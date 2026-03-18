from django.utils.deprecation import MiddlewareMixin

from .auth import JWTError, decode_jwt
from .models import User
from .services import is_token_blacklisted


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.erp_user = None
        request.jwt_payload = None

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None

        try:
            payload = decode_jwt(token)
        except JWTError:
            return None

        if is_token_blacklisted(payload.get("jti", "")):
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        try:
            user = User.objects.select_related("role").get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None

        request.erp_user = user
        request.jwt_payload = payload
        return None
