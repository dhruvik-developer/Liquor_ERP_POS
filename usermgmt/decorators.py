import json
from functools import wraps

from django.http import JsonResponse

from .services import has_permission, has_store_access


def json_error(message: str, status: int):
    return JsonResponse({"error": message}, status=status)


def parse_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload")


def require_auth(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not getattr(request, "erp_user", None):
            return json_error("Authentication required", 401)
        return view_func(request, *args, **kwargs)

    return _wrapped


def require_permission(permission_code: str, store_kwarg: str | None = None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "erp_user", None)
            if not user:
                return json_error("Authentication required", 401)
            if not has_permission(user, permission_code):
                return json_error("Permission denied", 403)
            if store_kwarg:
                store_id = kwargs.get(store_kwarg)
                if store_id is not None and not has_store_access(user, int(store_id)):
                    return json_error("Store access denied", 403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
