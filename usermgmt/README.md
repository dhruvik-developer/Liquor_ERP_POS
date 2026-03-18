# User Management Module (RBAC + Multi-Store)

## Folder Structure

- `usermgmt/models.py`: User, Role, Permission, mappings, token blacklist
- `usermgmt/services.py`: Effective permission resolution and assignment logic
- `usermgmt/auth.py`: JWT encode/decode (HS256)
- `usermgmt/drf_auth.py`: DRF JWT authentication class
- `usermgmt/serializers.py`: Request/response validation serializers
- `usermgmt/views.py`: DRF `GenericAPIView` class-based handlers
- `usermgmt/urls.py`: API route map

## Data Model

- `User`
- `Role`
- `Permission`
- `RolePermission`
- `UserPermissionOverride`
- `UserStoreMapping`
- `Store`
- `AuthTokenBlacklist`

## Permission Resolution Logic

1. If `is_super_admin=True`, all permissions are allowed.
2. Start with role permissions from `RolePermission`.
3. Apply user overrides:
- `is_allowed=True` adds permission.
- `is_allowed=False` removes permission.
4. Store access is validated separately from `UserStoreMapping`.

## API Routes

Base path: `/api/`

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/access-check?permission_code=users_view&store_id=1`
- `POST /users`
- `GET /users`
- `GET /users/:id`
- `PUT /users/:id`
- `DELETE /users/:id`
- `POST /roles`
- `GET /roles`
- `POST /permissions`
- `GET /permissions`
- `POST /users/:id/assign-role`
- `POST /roles/:id/assign-permissions`
- `POST /users/:id/permission-overrides`
- `POST /users/:id/assign-stores`
- `GET /stores`

## Example Flow

### 1) Create permission (dynamic)

```bash
curl -X POST http://localhost:8000/api/permissions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"module":"users","action":"view","code":"users_view"}'
```

### 2) Create role

```bash
curl -X POST http://localhost:8000/api/roles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Manager","description":"Store manager"}'
```

### 3) Attach permissions to role

```bash
curl -X POST http://localhost:8000/api/roles/2/assign-permissions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_ids":[1,2,3]}'
```

### 4) Create user with role

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Cashier One",
    "email":"cashier1@example.com",
    "password":"StrongPass@123",
    "mobile_number":"9999999999",
    "role_id":2,
    "store_ids":[1]
  }'
```

### 5) Override one permission for user

```bash
curl -X POST http://localhost:8000/api/users/3/permission-overrides \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"overrides":[{"permission_id":5,"is_allowed":false}]}'
```

### 6) Validate effective access

```bash
curl "http://localhost:8000/api/auth/access-check?permission_code=sales_create&store_id=1" \
  -H "Authorization: Bearer <token>"
```

## Run

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```
