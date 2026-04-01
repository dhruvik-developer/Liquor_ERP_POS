from django.contrib.auth.hashers import check_password
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .drf_auth import JWTAuthentication
from .models import Permission, Role, Store, User
from .serializers import (
    AssignRolePermissionsSerializer,
    AssignRoleSerializer,
    AssignStoresSerializer,
    LoginSerializer,
    PermissionCreateSerializer,
    PermissionSerializer,
    RoleCreateSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserPermissionOverrideSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import (
    assign_role_permissions,
    assign_user_stores,
    blacklist_token,
    get_effective_permission_codes,
    has_permission,
    has_store_access,
    upsert_user_permission_overrides,
)


class BaseERPAPIView(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def deny(self, message="Permission denied", status_code=status.HTTP_403_FORBIDDEN):
        return Response({"status": False, "message": message, "data": {}}, status=status_code)

    def allow(self, message, data=None, status_code=status.HTTP_200_OK):
        return Response({"status": True, "message": message, "data": data or {}}, status=status_code)

    def enforce_permission(self, request, permission_code):
        if not has_permission(request.user, permission_code):
            return self.deny("Permission denied", status.HTTP_403_FORBIDDEN)
        return None


class LoginViewSet(generics.GenericAPIView):
    serializer_class = LoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["login_identifier"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.select_related("role").get(email=identifier, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"status": False, "message": "Invalid credentials", "data": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not check_password(password, user.password):
            return Response(
                {"status": False, "message": "Invalid credentials", "data": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        response_data = {
            "name": user.name,
            "email": user.email,
            "tokens": {
                "access_token": access_token,
                "refresh_token": str(refresh),
                "token_type": "Bearer",
            },
            "user": UserSerializer(user).data,
        }
        return Response(
            {"status": True, "message": "Login successfully", "data": response_data},
            status=status.HTTP_200_OK,
        )


class TokenRefreshViewSet(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token") or request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"status": False, "message": "refresh_token is required", "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
        except TokenError:
            return Response(
                {"status": False, "message": "Invalid or expired refresh token", "data": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "status": True,
                "message": "Token refreshed successfully",
                "data": {
                    "tokens": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "Bearer",
                    }
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutViewSet(BaseERPAPIView):
    def post(self, request):
        refresh_token = request.data.get("refresh_token") or request.data.get("refresh")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                return self.deny("Invalid refresh token", status.HTTP_400_BAD_REQUEST)

        payload = getattr(request, "jwt_payload", {}) or {}
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            blacklist_token(request.user, jti, exp)
        return self.allow("Logged out successfully")


class UserViewSet(BaseERPAPIView):
    def get(self, request):
        denied = self.enforce_permission(request, "users_view")
        if denied:
            return denied
        
        queryset = User.objects.select_related("role").prefetch_related("user_store_mappings")
        return self.allow("User list", {"results": UserSerializer(queryset, many=True).data})

    def post(self, request):
        denied = self.enforce_permission(request, "users_create")
        if denied:
            return denied

        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if User.objects.filter(email=payload["email"]).exists():
            return self.deny("Email already exists", status.HTTP_409_CONFLICT)

        user = User(
            name=payload["name"],
            email=payload["email"],
            mobile_number=payload.get("mobile_number", ""),
            is_active=payload.get("is_active", True),
            is_super_admin=payload.get("is_super_admin", False),
            role_id=payload.get("role_id"),
        )
        user.set_password(payload["password"])
        user.save()

        if payload.get("store_ids"):
            assign_user_stores(user.id, payload["store_ids"])

        user = User.objects.select_related("role").prefetch_related("user_store_mappings").get(id=user.id)
        return self.allow("User created successfully", UserSerializer(user).data, status.HTTP_201_CREATED)


class UserDetailViewSet(BaseERPAPIView):
    def get_object(self, user_id):
        return User.objects.select_related("role").prefetch_related("user_store_mappings").filter(id=user_id).first()

    def get(self, request, user_id):
        denied = self.enforce_permission(request, "users_view")
        if denied:
            return denied

        user = self.get_object(user_id)
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)
        return self.allow("User details", UserSerializer(user).data)

    def put(self, request, user_id):
        denied = self.enforce_permission(request, "users_edit")
        if denied:
            return denied

        user = self.get_object(user_id)
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)

        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        for field in ["name", "mobile_number", "is_active", "is_super_admin", "role_id"]:
            if field in payload:
                setattr(user, field, payload[field])

        if payload.get("email") and payload["email"] != user.email:
            if User.objects.filter(email=payload["email"]).exclude(id=user.id).exists():
                return self.deny("Email already exists", status.HTTP_409_CONFLICT)
            user.email = payload["email"]

        if payload.get("password"):
            user.set_password(payload["password"])

        user.save()

        if "store_ids" in payload:
            assign_user_stores(user.id, payload.get("store_ids", []))

        user = User.objects.select_related("role").prefetch_related("user_store_mappings").get(id=user.id)
        return self.allow("User updated successfully", UserSerializer(user).data)

    def delete(self, request, user_id):
        denied = self.enforce_permission(request, "users_delete")
        if denied:
            return denied

        user = self.get_object(user_id)
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)
        user.delete()
        return self.allow("User deleted")


class RoleViewSet(BaseERPAPIView):
    def get(self, request):
        denied = self.enforce_permission(request, "settings_view")
        if denied:
            return denied

        queryset = Role.objects.prefetch_related("role_permissions")
        return self.allow("Role list", {"results": RoleSerializer(queryset, many=True).data})

    def post(self, request):
        denied = self.enforce_permission(request, "settings_create")
        if denied:
            return denied

        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if Role.objects.filter(name=payload["name"]).exists():
            return self.deny("Role already exists", status.HTTP_409_CONFLICT)

        role = Role.objects.create(name=payload["name"], description=payload.get("description", ""))
        if payload.get("permission_ids"):
            assign_role_permissions(role.id, payload["permission_ids"])

        role = Role.objects.prefetch_related("role_permissions").get(id=role.id)
        return self.allow("Role created successfully", RoleSerializer(role).data, status.HTTP_201_CREATED)


class PermissionViewSet(BaseERPAPIView):
    def get(self, request):
        denied = self.enforce_permission(request, "settings_view")
        if denied:
            return denied

        queryset = Permission.objects.all().order_by("module", "action")
        return self.allow("Permission list", {"results": PermissionSerializer(queryset, many=True).data})

    def post(self, request):
        denied = self.enforce_permission(request, "settings_create")
        if denied:
            return denied

        serializer = PermissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if Permission.objects.filter(code=payload["code"]).exists():
            return self.deny("Permission code already exists", status.HTTP_409_CONFLICT)

        permission = Permission.objects.create(**payload)
        return self.allow("Permission created successfully", PermissionSerializer(permission).data, status.HTTP_201_CREATED)


class AssignRoleToUserViewSet(BaseERPAPIView):
    serializer_class = AssignRoleSerializer

    def post(self, request, user_id):
        denied = self.enforce_permission(request, "users_edit")
        if denied:
            return denied

        user = User.objects.filter(id=user_id).first()
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_id = serializer.validated_data["role_id"]

        role = Role.objects.filter(id=role_id).first()
        if not role:
            return self.deny("Role not found", status.HTTP_404_NOT_FOUND)

        user.role = role
        user.save(update_fields=["role", "updated_at"])
        return self.allow("Role assigned")


class AssignPermissionsToRoleViewSet(BaseERPAPIView):
    serializer_class = AssignRolePermissionsSerializer

    def post(self, request, role_id):
        denied = self.enforce_permission(request, "settings_edit")
        if denied:
            return denied

        role = Role.objects.filter(id=role_id).first()
        if not role:
            return self.deny("Role not found", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assign_role_permissions(role.id, serializer.validated_data["permission_ids"])
        return self.allow("Role permissions updated")


class UserPermissionOverrideViewSet(BaseERPAPIView):
    serializer_class = UserPermissionOverrideSerializer

    def post(self, request, user_id):
        denied = self.enforce_permission(request, "users_edit")
        if denied:
            return denied

        user = User.objects.filter(id=user_id).first()
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upsert_user_permission_overrides(user_id, serializer.validated_data["overrides"])
        return self.allow("User permission overrides updated")


class AssignStoresToUserViewSet(BaseERPAPIView):
    serializer_class = AssignStoresSerializer

    def post(self, request, user_id):
        denied = self.enforce_permission(request, "users_edit")
        if denied:
            return denied

        user = User.objects.filter(id=user_id).first()
        if not user:
            return self.deny("User not found", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assign_user_stores(user_id, serializer.validated_data["store_ids"])
        return self.allow("User stores updated")


class StoreViewSet(BaseERPAPIView):
    def get(self, request):
        denied = self.enforce_permission(request, "settings_view")
        if denied:
            return denied

        stores = Store.objects.filter(is_active=True).order_by("name")
        data = [{"id": s.id, "name": s.name, "code": s.code} for s in stores]
        return self.allow("Store list", {"results": data})


class AccessCheckViewSet(BaseERPAPIView):
    def get(self, request):
        permission_code = request.query_params.get("permission_code")
        store_id = request.query_params.get("store_id")

        parsed_store_id = int(store_id) if store_id and store_id.isdigit() else None
        data = {
            "user_id": request.user.id,
            "permission_code": permission_code,
            "has_permission": has_permission(request.user, permission_code) if permission_code else None,
            "store_id": parsed_store_id,
            "has_store_access": has_store_access(request.user, parsed_store_id) if parsed_store_id else None,
            "effective_permissions": sorted(get_effective_permission_codes(request.user)),
        }
        return self.allow("Access evaluation", data)
