.PHONY: run init worker demo reset kpi

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

init:
	python scripts/init_db.py

worker:
	python worker.py

demo:
	./demo.sh

reset:
	./reset_demo.sh

kpi:
	curl -s http://127.0.0.1:8000/kpi && echo
