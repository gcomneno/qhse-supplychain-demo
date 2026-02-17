# Sequence Diagram — JWT + RBAC Enforcement

This sequence describes how authentication and authorization (RBAC) work in the API:
- `/auth/login` returns a JWT containing a `role` claim.
- Protected endpoints enforce access via a FastAPI dependency (`require_role([...])`).

---

## 1) Login → JWT with role claim

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI API
    participant AuthRoute as /auth/login
    participant AuthSvc as Auth Logic (static users)
    participant JWT as JWT Encoder (HS256)

    Client->>API: POST /auth/login {username,password}
    API->>AuthRoute: route handler
    AuthRoute->>AuthSvc: validate credentials (static demo users)
    alt invalid credentials
        AuthSvc-->>AuthRoute: invalid
        AuthRoute-->>Client: 401 Unauthorized
    else valid credentials
        AuthSvc-->>AuthRoute: user role (e.g., "quality")
        AuthRoute->>JWT: encode({sub=username, role=role, exp=...})
        JWT-->>AuthRoute: access_token
        AuthRoute-->>Client: 200 OK {access_token, token_type="bearer"}
    end
```

### Notes

* The issued token embeds the **role claim** (e.g., `"role": "quality"`).
* Token expiry is handled via `exp`.

---

## 2) Protected endpoint → dependency RBAC check (happy path)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI API
    participant Dep as require_role([...]) dependency
    participant JWT as JWT Decoder/Verifier (HS256)
    participant Route as Protected Route Handler

    Client->>API: GET /kpi (Authorization: Bearer <JWT>)
    API->>Dep: resolve dependency (before handler)
    Dep->>JWT: decode + verify signature + verify exp
    JWT-->>Dep: claims {sub, role, exp, ...}
    Dep->>Dep: check role ∈ allowed_roles
    Dep-->>API: ok (user authorized)
    API->>Route: execute handler
    Route-->>Client: 200 OK (response)
```

### Notes

* Authorization happens **before** the route handler runs.
* Services don’t re-check auth: the API boundary is the enforcement point.

---

## 3) Missing/invalid token → 401 Not authenticated

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI API
    participant Dep as get_current_user / require_role
    participant JWT as JWT Decoder/Verifier

    Client->>API: GET /kpi (no Authorization header)
    API->>Dep: resolve dependency
    Dep-->>Client: 401 Not authenticated
```

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI API
    participant Dep as get_current_user / require_role
    participant JWT as JWT Decoder/Verifier

    Client->>API: GET /kpi (Authorization: Bearer <bad/expired>)
    API->>Dep: resolve dependency
    Dep->>JWT: decode/verify
    alt invalid signature or expired token
        JWT-->>Dep: error
        Dep-->>Client: 401 Not authenticated
    end
```

---

## 4) Valid token but wrong role → 403 Forbidden

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI API
    participant Dep as require_role(["auditor","quality","admin"])
    participant JWT as JWT Decoder/Verifier

    Client->>API: GET /kpi (Authorization: Bearer <JWT role="procurement">)
    API->>Dep: resolve dependency
    Dep->>JWT: decode + verify
    JWT-->>Dep: claims {role="procurement", ...}
    Dep->>Dep: role not in allowed_roles
    Dep-->>Client: 403 Forbidden
```

---

## 5) Policy mapping lives at the endpoint (RBAC “at a glance”)

RBAC is expressed directly on endpoints via:
* `dependencies=[Depends(require_role([...]))]`

This makes authorization:
- explicit
- audit-friendly
- easy to review in code reviews
