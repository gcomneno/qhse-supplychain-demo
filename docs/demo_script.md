# login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"quality","password":"quality"}'

# usa token
curl http://localhost:8000/kpi \
  -H "Authorization: Bearer <TOKEN>"
