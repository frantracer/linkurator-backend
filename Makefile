build:
	docker build -t linkurator-api .

clean:
	docker rm -f linkurator-api

run: clean build
	docker run --name linkurator-api -p 9000:8080 -d linkurator-api

check-linting: clean build
	docker run --name linkurator-api --rm linkurator-api /usr/local/bin/python -m mypy --strict .
	docker run --name linkurator-api --rm linkurator-api /bin/bash -c "find . -name *.py | xargs pylint"

test: clean build
	docker run --name linkurator-api linkurator-api /usr/local/bin/python -m pytest -v /app/tests

run-dev:
	cd src; uvicorn main:app --reload --host 0.0.0.0 --port 9000

check-linting-dev:
	cd src; mypy --strict .
	cd src; find . -name *.py | xargs pylint

test-dev:
	cd src; pytest -v ./tests
