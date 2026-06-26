PYTHON ?= .venv/bin/python

.PHONY: rebuild serve

rebuild:
	rm -rf frontend/dist
	cd frontend && npm run build
	PYTHONPATH=src $(PYTHON) -m adarian serve

serve:
	PYTHONPATH=src $(PYTHON) -m adarian serve
