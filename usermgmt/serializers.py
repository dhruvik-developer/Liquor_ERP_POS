from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Permission, Role, User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        if not username and not email:
            raise serializers.ValidationError("username or email is required")
        attrs["login_identifier"] = email or username
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Password confirmation does not match"})

        try:
            validate_password(attrs["new_password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc

        return attrs


class ForgotPasswordAdminCheckSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "module", "action", "code"]


class RoleSerializer(serializers.ModelSerializer):
    permission_ids = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permission_ids"]

    def get_permission_ids(self, obj):
        return list(obj.role_permissions.values_list("permission_id", flat=True))


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    store_ids = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "user_id",
            "gender",
            "first_name",
            "last_name",
            "email",
            "mobile_number",
            "address_1",
            "address_2",
            "city",
            "state",
            "zip_code",
            "phone",
            "phone_ext",
            "country",
            "is_active",
            "is_super_admin",
            "role",
            "store_ids",
            "permissions",
            "created_at",
            "updated_at",
        ]

    def get_role(self, obj):
        if not obj.role:
            return None
        return {"id": obj.role.id, "name": obj.role.name}

    def get_store_ids(self, obj):
        return list(obj.user_store_mappings.values_list("store_id", flat=True))

    def get_permissions(self, obj):
        from .services import get_effective_permission_codes

        return sorted(get_effective_permission_codes(obj))


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    user_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    mobile_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone_ext = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(required=False, default=True)
    is_super_admin = serializers.BooleanField(required=False, default=False)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    store_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    user_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    mobile_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone_ext = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False)
    is_active = serializers.BooleanField(required=False)
    is_super_admin = serializers.BooleanField(required=False)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    store_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class RoleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    permission_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class RoleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    permission_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class PermissionCreateSerializer(serializers.Serializer):
    module = serializers.CharField(max_length=100)
    action = serializers.CharField(max_length=50)
    code = serializers.CharField(max_length=150)


class AssignRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()


class AssignRolePermissionsSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField())


class UserPermissionOverrideItemSerializer(serializers.Serializer):
    permission_id = serializers.IntegerField()
    is_allowed = serializers.BooleanField()


class UserPermissionOverrideSerializer(serializers.Serializer):
    overrides = UserPermissionOverrideItemSerializer(many=True)


class AssignStoresSerializer(serializers.Serializer):
    store_ids = serializers.ListField(child=serializers.IntegerField())
