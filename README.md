# QHSE Supply Chain Demo (Sinergest-like) — FastAPI + SQLAlchemy + SQLite

Mini piattaforma QHSE / Supply Chain con gestione **Non Conformità (NC)** su fornitori, architettura **event-driven affidabile** tramite **Outbox transazionale**, **worker idempotente** e **Audit Trail verificabile**.

L’obiettivo non è il framework, ma l’integrità del flusso:
prima garantire coerenza e tracciabilità, poi (eventualmente) scalare.

---

## Pitch (20 secondi)

Creo una Non Conformità e, nella stessa transazione DB, genero un evento Outbox.
Un worker idempotente consuma gli eventi e scrive un audit trail append-only.
I KPI riflettono in tempo reale lo stato operativo e il rischio fornitore.
È event-driven affidabile senza dipendere da broker esterni.

---

## Architettura (mini)

Client → FastAPI → DB (business + outbox)
                      |
                      ↓
                  worker.py (polling)
                      |
                      ↓
            audit_log + processed_events

- Outbox e dati business condividono la stessa transazione
- Worker idempotente evita duplicazioni
- Audit trail append-only garantisce tracciabilità

---

## Cosa dimostra (in pratica)

- Gestione **Supplier** e **NonConformity**
- Creazione NC → evento `NC_CREATED` in Outbox (transazionale)
- Chiusura NC → evento `NC_CLOSED`
- Aggiornamento certificazione → evento `SUPPLIER_CERT_UPDATED`
- Worker idempotente con deduplica su `processed_events`
- Audit trail persistente su `audit_log`
- Endpoint `/kpi` con metriche operative e rischio fornitore

---

## KPI disponibili

`GET /kpi`

Restituisce:

- `nc_open`
- `nc_open_high`
- `nc_closed`
- `outbox_pending`
- `outbox_failed`
- `suppliers_at_risk`
- `audit_events_total`

### Regola rischio fornitore

Un fornitore è "a rischio" se:

- certificazione scaduta  
**oppure**
- almeno una NC `high` aperta

---

## Requisiti

- Python 3.12+
- (opzionale) `sqlite3` CLI

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic
python scripts/init_db.py
```

## Avvio API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


Health check:
curl -s http://127.0.0.1:8000/health

## Demo automatica (consigliata)

Esegue workflow completo:
./reset_demo.sh
./demo.sh


Mostra:
- Creazione Supplier
- Creazione NC (severity=low)
- Consumo evento NC_CREATED
- Chiusura NC
- Aggiornamento certificazione via PATCH
- KPI che passa da suppliers_at_risk=0 a 1

Demo manuale (API → Outbox → Worker → Audit)
1) Crea fornitore
curl -s -X POST http://127.0.0.1:8000/suppliers \
  -H "Content-Type: application/json" \
  -d '{"name":"Beta Metals","certification_expiry":"2026-06-30"}'

2) Crea NC
curl -s -X POST http://127.0.0.1:8000/ncs \
  -H "Content-Type: application/json" \
  -d '{"supplier_id":1,"severity":"high","description":"Certificato materiale mancante"}'

3) Avvia worker
python worker.py

4) Aggiorna certificazione (PATCH parziale)
curl -s -X PATCH http://127.0.0.1:8000/suppliers/1/certification \
  -H "Content-Type: application/json" \
  -d '{"certification_expiry":"2020-01-01"}'

## Verifica DB (opzionale)
sqlite3 qhse_demo.sqlite3 "select id,event_type,status from outbox_events;"
sqlite3 qhse_demo.sqlite3 "select id,action,entity_type,entity_id from audit_log;"

## Decisioni architetturali

Outbox pattern
Evento persistito nella stessa transazione dei dati business.

Worker idempotente
Deduplica tramite tabella processed_events.

Audit trail append-only
Registro verificabile delle azioni di sistema.

## Nota
Il design è broker-agnostico: il worker polling può essere sostituito da un message broker (Kafka, RabbitMQ, ecc.) senza modificare il modello dati o il pattern Outbox.
