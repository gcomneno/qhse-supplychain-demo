# Security Model

This document describes authentication and authorization design decisions.

The system uses:
- JWT (HS256)
- Role-Based Access Control (RBAC)
- Endpoint-level authorization enforcement

---

# 1. Authentication (JWT)

Authentication is performed via:

```

POST /auth/login

````

Valid demo users:

| Username     | Role         |
|--------------|--------------|
| quality      | quality      |
| procurement  | procurement  |
| auditor      | auditor      |
| admin        | admin        |

On successful login:

- A JWT is issued
- The token includes:
  - `sub` (username)
  - `role`
  - `exp`

Example payload:

```json
{
  "sub": "quality",
  "role": "quality",
  "exp": 1700000000
}
````

---

# 2. Authorization Model (RBAC)

Authorization is enforced via FastAPI dependencies:

```python
dependencies=[Depends(require_role(["auditor", "admin"]))]
```

The dependency performs:
1. JWT decoding
2. Signature validation
3. Expiration validation
4. Role verification

If:
- Token missing/invalid → **401 Not authenticated**
- Role not allowed → **403 Forbidden**

---

# 3. Endpoint Role Matrix

This table summarizes access control policy:

| Endpoint                              | Read Roles                           | Write Roles        |
| ------------------------------------- | ------------------------------------ | ------------------ |
| `POST /auth/login`                    | Public                               | Public             |
| `GET /kpi`                            | auditor, quality, admin              | —                  |
| `GET /suppliers`                      | auditor, quality, procurement, admin | —                  |
| `POST /suppliers`                     | —                                    | procurement, admin |
| `GET /suppliers/{id}`                 | auditor, quality, procurement, admin | —                  |
| `PATCH /suppliers/{id}/certification` | —                                    | procurement, admin |
| `GET /ncs`                            | auditor, quality, procurement, admin | —                  |
| `POST /ncs`                           | —                                    | quality, admin     |
| `PATCH /ncs/{id}/close`               | —                                    | quality, admin     |
| `GET /audit-log`                      | auditor, admin                       | —                  |

---

# 4. Enforcement Location

Authorization is enforced **at the API boundary**.

Service functions assume:

* Valid authentication
* Valid authorization

This ensures:

* Business logic remains clean
* Authorization policy is explicit per endpoint
* Role policies are visible in route definitions

---

# 5. Design Trade-offs

## Why Static Users?

The project focuses on RBAC structure, not identity lifecycle.

Full user management (password hashing, user persistence, refresh tokens) would distract from architectural focus.

## Why Role in JWT?

Embedding role in the token:

* Avoids DB lookups per request
* Keeps authorization stateless
* Simplifies demo architecture

In production, roles might be:

* Retrieved from DB
* Managed via IAM
* Refreshed via short-lived access tokens

---

# 6. Production Considerations (Not Implemented)

In a production system, we would likely add:
- Refresh tokens
- Password hashing (bcrypt/argon2)
- Token rotation
- External identity provider
- Structured security logging
- Rate limiting
- Centralized policy enforcement

---

# 7. Security Boundaries

Security is enforced in three steps:
1. JWT validation (authentication)
2. Role verification (authorization)
3. Business execution

Failure at step 1 → 401
Failure at step 2 → 403

No business logic is executed before successful authorization.
