from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Role(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Permission(TimeStampedModel):
    module = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    code = models.CharField(max_length=150, unique=True)

    class Meta:
        unique_together = ("module", "action")
        indexes = [models.Index(fields=["module", "action"])]

    def __str__(self):
        return self.code


class RolePermission(TimeStampedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")

    class Meta:
        unique_together = ("role", "permission")


class Store(TimeStampedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_super_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="users")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return self.email


class UserPermissionOverride(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="permission_overrides")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="user_overrides")
    is_allowed = models.BooleanField()

    class Meta:
        unique_together = ("user", "permission")


class UserStoreMapping(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_store_mappings")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="store_user_mappings")

    class Meta:
        unique_together = ("user", "store")


class AuthTokenBlacklist(TimeStampedModel):
    jti = models.CharField(max_length=128, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blacklisted_tokens")
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["jti"]), models.Index(fields=["expires_at"])]
