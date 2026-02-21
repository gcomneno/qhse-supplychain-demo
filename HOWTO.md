# Makefile – Comandi disponibili
Questo progetto usa `make` come “control panel” per: avvio stack, test, smoke test e operazioni di base.

---

## Prerequisiti
- `make`
- Docker + Docker Compose (plugin `docker compose`)
- Python virtualenv per i comandi locali (`make run`, `make worker`) se li usi fuori dai container

---

## Panoramica rapida
| Obiettivo | Comando |
|----------|---------|
| Vedere l’elenco comandi | `make` oppure `make help` |
| Eseguire i test (pytest + DB + migrazioni) | `make test` |
| Avviare stack completo | `make up` |
| Spegnere stack | `make down` |
| Vedere stato container | `make ps` |
| Seguire i log | `make logs` |
| Eseguire smoke test (integrazione) | `make smoke` |
| Applicare migrazioni (Alembic) | `make migrate` |
| Wipe DB (⚠️ distruttivo) | `make reset-db` |

---

## Comandi “dev local”

### `make run`
Avvia l’API **localmente** con reload.

- Host: `127.0.0.1`
- Porta: `8000`
- Usa `.env`

```bash
make run
````

### `make worker`

Avvia il worker **localmente** (non in Docker).

```bash
make worker
```

---

## Stack Docker (integrazione)

### `make up`

Avvia lo stack minimo per la demo:

* `db`
* `api`
* `worker`
* `prometheus`

```bash
make up
```

### `make ps`

Mostra lo stato dei container.

```bash
make ps
```

### `make logs`

Segue i log di tutti i servizi (ultime 200 righe, poi follow).

```bash
make logs
```

### `make down`

Ferma lo stack.

```bash
make down
```

### `make reset-db` (⚠️ distruttivo)

Spegne lo stack e rimuove i volumi (quindi **cancella i dati** del DB).

```bash
make reset-db
```

---

## Database e migrazioni

### `make migrate`

Applica le migrazioni Alembic al DB locale (compose).

```bash
make migrate
```

> Nota: `make migrate` usa lo stesso flusso di `make test-db-migrate` (db up + wait + alembic).

### `make init` (deprecato)

Comando mantenuto solo per compatibilità: reindirizza a `make migrate`.

```bash
make init
```

---

## Test

### `make test`

Esegue la pipeline di test completa:

1. avvia `db` in Docker
2. attende che Postgres sia pronto
3. applica migrazioni Alembic (`upgrade head`)
4. esegue `pytest -q` con tracing disabilitato

```bash
make test
```

### Comandi interni usati dai test (di solito non servono a mano)

* `make test-db-up` → avvia solo il DB
* `make test-db-wait` → aspetta readiness Postgres
* `make test-db-migrate` → migrazioni Alembic su DB locale

---

## Smoke test

### `make smoke`

Esegue `./scripts/smoke.sh`.

Scopo: verificare che lo stack “parli” davvero (API, auth, DB, worker, metrics, Prometheus) senza fare test “fini” come pytest.

```bash
make smoke
```

---

## Flusso consigliato

### Validare il codice (CI mentale)

```bash
make test
```

### Validare l’integrazione (stack “vivo”)

```bash
make up
make smoke
make down
```
