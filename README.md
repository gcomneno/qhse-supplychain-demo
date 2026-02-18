# QHSE Supply Chain Backend

### Reliability-Oriented Architecture Demo (FastAPI + SQLAlchemy + Postgres)

---

## 1. Overview

This project is a reliability-focused backend demo for a simplified QHSE (Quality, Health, Safety, Environment) supply chain domain.

It is intentionally designed around:

* **Consistency**
* **Transaction boundaries**
* **Role-based access control**
* **Idempotent background processing**
* **Clear architectural layering**

The goal is not feature richness, but architectural correctness.

---

## 2. High-Level Architecture

```
             ┌──────────────┐
             │   FastAPI    │
             │  API Layer   │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │   Services   │
             │  (Business)  │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │ SQLAlchemy   │
             │ Persistence  │
             └──────┬───────┘
                    │
                    ▼
               PostgreSQL
                    │
                    ▼
            ┌────────────────┐
            │  Worker        │
            │  (Outbox Poll) │
            └────────────────┘
```

### Layers

* **API layer**: request validation, RBAC enforcement
* **Service layer**: business rules and transaction boundaries
* **Persistence layer**: SQLAlchemy 2.0 (sync)
* **Worker**: background polling consumer for transactional outbox

Dependencies flow strictly downward.

---

## 3. Core Features

### Domain

* Suppliers
* Non-Conformities (NCs)
* Audit Log
* KPI aggregation
* Risk detection logic

### API

* CRUD-style endpoints (minimalistic)
* Pagination (`limit`, `offset`)
* Optional filters (`/ncs?status=OPEN&severity=high`)
* Read-only audit log (`/audit-log`)

### Security

* JWT authentication
* Static demo users
* RBAC enforcement per endpoint

### Reliability

* Transactional Outbox pattern
* Idempotent worker processing
* Deterministic tests

---

## 4. Security Model (JWT + RBAC)

Authentication is handled via JWT (HS256).

Demo users:

| Username    | Role        |
| ----------- | ----------- |
| quality     | quality     |
| procurement | procurement |
| auditor     | auditor     |
| admin       | admin       |

RBAC is enforced via dependency injection.

Examples:

* `/suppliers` write → `procurement`, `admin`
* `/ncs` write → `quality`, `admin`
* `/kpi` read → `auditor`, `quality`, `admin`
* `/audit-log` read → `auditor`, `admin`

This is minimal but structurally correct RBAC.

---

## 5. Consistency Model — Transactional Outbox

Side effects are not executed directly inside business logic.

Instead:

1. A domain event is written to `outbox_events` within the same DB transaction.
2. A background worker polls pending events.
3. The worker processes them.
4. Processed events are recorded for idempotency.

This ensures:

* No partial commits
* Safe retries
* Failure isolation
* Deterministic processing

This is a simplified but production-realistic reliability pattern.

---

## 6. Running the System

### Recommended: Docker Compose

```bash
docker compose up --build
```

Services:

* `postgres`
* `api`
* `worker`
* `migrate` (Alembic baseline)

API available at:

```
http://localhost:8000
http://localhost:8000/docs
```

Swagger UI includes Bearer JWT authorization.

---

### Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

---

## 7. API Overview

### Auth

```
POST /auth/login
```

Returns JWT.

### Suppliers

```
POST   /suppliers
GET    /suppliers
GET    /suppliers/{id}
PATCH  /suppliers/{id}/certification
```

### Non-Conformities

```
POST   /ncs
PATCH  /ncs/{id}/close
GET    /ncs?status=OPEN&severity=high
```

### Audit Log

```
GET /audit-log?limit=20&offset=0
```

### KPI

```
GET /kpi
```

Aggregates:

* Open NCs
* High severity NCs
* Closed NCs
* Outbox state
* Suppliers at risk

---

## 8. Testing Strategy

Tests use:

* SQLite (isolated per test run)
* Deterministic auth
* Transactional session fixture
* Worker idempotency verification
* RBAC smoke tests

Tests validate:

* Outbox not written on rollback
* Worker idempotency
* RBAC enforcement
* Filter correctness
* Pagination behavior

All tests are expected to pass with:

```bash
pytest -q
```

---

## 9. Design Decisions & Trade-offs

### Why SQLAlchemy Sync?

* Simpler mental model
* Deterministic transaction handling
* No async DB complexity for this scope

### Why SQLite for Tests?

* Fast
* Isolated
* No external dependency
* Reproducible

### Why Postgres in Docker?

* Production-realistic behavior
* Real DDL and type enforcement
* Separate from test environment

### Why Static Users?

* Demo simplicity
* Focus on RBAC structure, not user management

### What Would Change in Production?

* Persistent user model
* Refresh tokens
* Centralized logging
* Observability (metrics/tracing)
* Structured audit metadata
* Background worker orchestration (e.g., queue-based)

---

## 10. Purpose of This Project

This is not a CRUD tutorial.

It is a small but coherent example of:

* Layered backend architecture
* Explicit transaction boundaries
* Reliability-oriented design
* Clear role-based authorization
* Separation of sync API and async processing

It is intended as a discussion base for backend architecture interviews.

#### What This Project Is NOT

This project is intentionally scoped.

It is not:

- ❌ A production-ready identity system  
  (Users are static. No password hashing lifecycle, no refresh tokens, no IAM integration.)

- ❌ A high-throughput event streaming system  
  (No Kafka, no RabbitMQ, no distributed message broker.)

- ❌ An async-first microservices architecture  
  (The system uses synchronous SQLAlchemy by design for clarity of transaction boundaries.)

- ❌ A horizontally scalable event processor  
  (The worker uses a polling model and a single database as coordination layer.)

- ❌ A feature-complete QHSE platform  
  (The domain is intentionally minimal to focus on architecture.)

- ❌ A CRUD tutorial  
  (The goal is reliability patterns, not endpoint count.)

---

#### Why These Choices?

The project prioritizes:
- Explicit transaction boundaries
- Atomic domain + event persistence
- Idempotent background processing
- Clear RBAC enforcement at API boundary
- Deterministic behavior under failure

It intentionally favors architectural clarity over feature density.

---

#### How It Would Evolve in Production

If evolved toward production scale, the system would likely introduce:

- External identity provider
- Token rotation and refresh
- Message broker instead of DB polling
- Observability stack (metrics, tracing)
- Retry backoff strategies
- Dead-letter queue
- Horizontal worker scaling
- Read replicas for analytics endpoints

These extensions are deliberately excluded to keep the architectural core visible and reviewable.
