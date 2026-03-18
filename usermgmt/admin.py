from django.contrib import admin

from .models import (
    AuthTokenBlacklist,
    Permission,
    Role,
    RolePermission,
    Store,
    User,
    UserPermissionOverride,
    UserStoreMapping,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "role", "is_active", "is_super_admin")
    search_fields = ("email", "name", "mobile_number")
    list_filter = ("is_active", "is_super_admin", "role")


admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(UserPermissionOverride)
admin.site.register(Store)
admin.site.register(UserStoreMapping)
admin.site.register(AuthTokenBlacklist)
