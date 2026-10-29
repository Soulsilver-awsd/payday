.PHONY: install run test lint format migrate

install:
	pip install -r requirements-dev.txt

run:
	flask --app wsgi run --debug

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

migrate:
	flask --app wsgi db upgrade
