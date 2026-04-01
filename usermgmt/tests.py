import json

from django.test import Client, TestCase

from .models import Permission, Role, RolePermission, Store, User, UserPermissionOverride, UserStoreMapping
from .services import get_effective_permission_codes, has_permission, has_store_access


class RBACServiceTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Manager")
        self.p_view = Permission.objects.create(module="users", action="view", code="users_view")
        self.p_edit = Permission.objects.create(module="users", action="edit", code="users_edit")
        RolePermission.objects.create(role=self.role, permission=self.p_view)

        self.user = User.objects.create(name="U", email="u@example.com", role=self.role)
        self.user.set_password("pass@1234")
        self.user.save()

    def test_role_permission_applies(self):
        self.assertTrue(has_permission(self.user, "users_view"))
        self.assertFalse(has_permission(self.user, "users_edit"))

    def test_user_override_denies_role_permission(self):
        UserPermissionOverride.objects.create(user=self.user, permission=self.p_view, is_allowed=False)
        self.assertFalse(has_permission(self.user, "users_view"))

    def test_user_override_adds_permission(self):
        UserPermissionOverride.objects.create(user=self.user, permission=self.p_edit, is_allowed=True)
        effective = get_effective_permission_codes(self.user)
        self.assertIn("users_edit", effective)

    def test_store_access(self):
        store = Store.objects.create(name="Store A", code="A1")
        self.assertFalse(has_store_access(self.user, store.id))
        UserStoreMapping.objects.create(user=self.user, store=store)
        self.assertTrue(has_store_access(self.user, store.id))


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(name="Admin")

        self.p_users_view = Permission.objects.create(module="users", action="view", code="users_view")
        self.p_settings_view = Permission.objects.create(module="settings", action="view", code="settings_view")
        self.p_settings_create = Permission.objects.create(module="settings", action="create", code="settings_create")

        RolePermission.objects.create(role=self.role, permission=self.p_users_view)
        RolePermission.objects.create(role=self.role, permission=self.p_settings_view)
        RolePermission.objects.create(role=self.role, permission=self.p_settings_create)

        self.user = User.objects.create(name="Admin", email="admin@example.com", role=self.role)
        self.user.set_password("Admin@12345")
        self.user.save()

    def test_login_and_access_check(self):
        response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"email": "admin@example.com", "password": "Admin@12345"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["data"]["tokens"]["access_token"]

        access_check = self.client.get(
            "/api/auth/access-check/?permission_code=users_view",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(access_check.status_code, 200)
        self.assertTrue(access_check.json()["data"]["has_permission"])
