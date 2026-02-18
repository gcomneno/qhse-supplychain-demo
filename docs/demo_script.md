## Auth (JWT)

### Login (quality)
```bash
TOKEN_Q=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"quality","password":"quality"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "$TOKEN_Q"
```

### Login (procurement)
```bash
TOKEN_P=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"procurement","password":"procurement"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "$TOKEN_P"
```

### Login (auditor)
```bash
TOKEN_A=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"auditor","password":"auditor"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "$TOKEN_A"
```

### Login (admin)
```bash
TOKEN_AD=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "$TOKEN_AD"
```

### Swagger UI: apri /docs → Authorize → incolla il token.
KPI (read: auditor/quality/admin)
```bash
curl -s http://localhost:8000/kpi -H "Authorization: Bearer $TOKEN_Q"
```

Forbidden example (procurement → 403):
```bash
curl -i http://localhost:8000/kpi -H "Authorization: Bearer $TOKEN_P"
```

Suppliers
Create (write: procurement/admin):
```bash
curl -s -X POST http://localhost:8000/suppliers \
  -H "Authorization: Bearer $TOKEN_P" \
  -H "Content-Type: application/json" \
  -d '{"name":"ACME","certification_expiry":null}'
```

Forbidden example (quality → 403):
```bash
curl -i -X POST http://localhost:8000/suppliers \
  -H "Authorization: Bearer $TOKEN_Q" \
  -H "Content-Type: application/json" \
  -d '{"name":"NOPE","certification_expiry":null}'
```

List (read: auditor/quality/procurement/admin):
```bash
curl -s "http://localhost:8000/suppliers?limit=20&offset=0" -H "Authorization: Bearer $TOKEN_A"
```

Nonconformities (NC)
Create (write: quality/admin):

# replace SUPPLIER_ID
```bash
curl -s -X POST http://localhost:8000/ncs \
  -H "Authorization: Bearer $TOKEN_Q" \
  -H "Content-Type: application/json" \
  -d '{"supplier_id":1,"severity":"high","description":"demo nc"}'
```

List + filters:
```bash
curl -s "http://localhost:8000/ncs?status=OPEN&severity=high&limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN_A"
```

Audit log (read-only: auditor/admin)
```bash
curl -s "http://localhost:8000/audit-log?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN_A"
```

Forbidden example (quality → 403):
```bash
curl -i "http://localhost:8000/audit-log" \
  -H "Authorization: Bearer $TOKEN_Q"
```
