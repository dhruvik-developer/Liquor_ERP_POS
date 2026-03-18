from django.urls import path

from .views import (
    AccessCheckViewSet,
    AssignPermissionsToRoleViewSet,
    AssignRoleToUserViewSet,
    AssignStoresToUserViewSet,
    LoginViewSet,
    LogoutViewSet,
    PermissionViewSet,
    RoleViewSet,
    StoreViewSet,
    UserDetailViewSet,
    UserPermissionOverrideViewSet,
    UserViewSet,
)

urlpatterns = [
    path("auth/login", LoginViewSet.as_view(), name="login"),
    path("auth/logout", LogoutViewSet.as_view(), name="logout"),
    path("auth/access-check", AccessCheckViewSet.as_view(), name="access-check"),
    path("users", UserViewSet.as_view(), name="users"),
    path("users/<int:user_id>", UserDetailViewSet.as_view(), name="user-detail"),
    path("roles", RoleViewSet.as_view(), name="roles"),
    path("permissions", PermissionViewSet.as_view(), name="permissions"),
    path("stores", StoreViewSet.as_view(), name="stores"),
    path("users/<int:user_id>/assign-role", AssignRoleToUserViewSet.as_view(), name="assign-role-to-user"),
    path("roles/<int:role_id>/assign-permissions", AssignPermissionsToRoleViewSet.as_view(), name="assign-permissions-to-role"),
    path("users/<int:user_id>/permission-overrides", UserPermissionOverrideViewSet.as_view(), name="user-permission-overrides"),
    path("users/<int:user_id>/assign-stores", AssignStoresToUserViewSet.as_view(), name="assign-stores-to-user"),
]
