from datetime import datetime, timezone

from django.db import transaction

from .models import (
    AuthTokenBlacklist,
    Permission,
    RolePermission,
    Store,
    User,
    UserPermissionOverride,
    UserStoreMapping,
)


def get_user_by_id(user_id: int) -> User:
    return User.objects.select_related("role").get(id=user_id)


def get_effective_permission_codes(user: User) -> set[str]:
    if user.is_super_admin:
        return set(Permission.objects.values_list("code", flat=True))

    role_codes = set()
    if user.role_id:
        role_codes = set(
            RolePermission.objects.filter(role_id=user.role_id)
            .select_related("permission")
            .values_list("permission__code", flat=True)
        )

    overrides = UserPermissionOverride.objects.filter(user=user).select_related("permission")
    allowed = {ov.permission.code for ov in overrides if ov.is_allowed}
    denied = {ov.permission.code for ov in overrides if not ov.is_allowed}

    return (role_codes | allowed) - denied


def has_permission(user: User, permission_code: str) -> bool:
    if not user.is_active:
        return False
    if user.is_super_admin:
        return True
    return permission_code in get_effective_permission_codes(user)


def has_store_access(user: User, store_id: int) -> bool:
    if user.is_super_admin:
        return True
    return UserStoreMapping.objects.filter(user=user, store_id=store_id, store__is_active=True).exists()


def blacklist_token(user: User, jti: str, expires_at_unix: int) -> None:
    expires_at = datetime.fromtimestamp(expires_at_unix, tz=timezone.utc)
    AuthTokenBlacklist.objects.get_or_create(jti=jti, defaults={"user": user, "expires_at": expires_at})


def is_token_blacklisted(jti: str) -> bool:
    return AuthTokenBlacklist.objects.filter(jti=jti).exists()


@transaction.atomic
def assign_role_permissions(role_id: int, permission_ids: list[int]) -> None:
    RolePermission.objects.filter(role_id=role_id).exclude(permission_id__in=permission_ids).delete()
    existing = set(
        RolePermission.objects.filter(role_id=role_id, permission_id__in=permission_ids).values_list("permission_id", flat=True)
    )
    to_create = [
        RolePermission(role_id=role_id, permission_id=pid)
        for pid in permission_ids
        if pid not in existing
    ]
    if to_create:
        RolePermission.objects.bulk_create(to_create)


@transaction.atomic
def upsert_user_permission_overrides(user_id: int, overrides: list[dict]) -> None:
    for ov in overrides:
        UserPermissionOverride.objects.update_or_create(
            user_id=user_id,
            permission_id=ov["permission_id"],
            defaults={"is_allowed": ov["is_allowed"]},
        )


@transaction.atomic
def assign_user_stores(user_id: int, store_ids: list[int]) -> None:
    valid_store_ids = set(Store.objects.filter(id__in=store_ids, is_active=True).values_list("id", flat=True))
    UserStoreMapping.objects.filter(user_id=user_id).exclude(store_id__in=valid_store_ids).delete()
    existing = set(
        UserStoreMapping.objects.filter(user_id=user_id, store_id__in=valid_store_ids).values_list("store_id", flat=True)
    )
    to_create = [
        UserStoreMapping(user_id=user_id, store_id=sid)
        for sid in valid_store_ids
        if sid not in existing
    ]
    if to_create:
        UserStoreMapping.objects.bulk_create(to_create)
