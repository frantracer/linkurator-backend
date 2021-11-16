docker-build:
	docker build -t linkurator-api .

docker-clean:
	docker rm -f linkurator-api

docker-run: docker-clean docker-build
	docker run --name linkurator-api -p 9000:8080 -d linkurator-api

docker-check-linting: docker-clean docker-build
	docker run --name linkurator-api --rm linkurator-api /usr/local/bin/python -m mypy --strict .
	docker run --name linkurator-api --rm linkurator-api /bin/bash -c "find . -name *.py | xargs pylint"

docker-test: docker-clean docker-build
	docker run --name linkurator-api linkurator-api /usr/local/bin/python -m pytest -v /app/tests

run:
	cd src; uvicorn main:app --reload --host 0.0.0.0 --port 9000

check-linting:
	cd src; mypy --strict .
	cd src; find . -name *.py | xargs pylint

test:
	cd src; pytest -v ./tests
