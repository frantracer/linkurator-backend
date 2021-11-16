

docker-build:
	docker build -t linkurator-api .

docker-clean:
	docker rm -f linkurator-api

docker-run: docker-clean docker-build
	docker run --name linkurator-api -p 9000:9000 -d linkurator-api

docker-check-linting: docker-clean docker-build
	docker run --name linkurator-api --rm linkurator-api make check-linting

docker-test: docker-clean docker-build
	docker run --name linkurator-api linkurator-api make test

setup:
	pip install -r requirements.txt

run:
	cd app; uvicorn server:app --host 0.0.0.0 --port 9000

dev-run:
	cd app; uvicorn server:app --reload --host 0.0.0.0 --port 9000

check-linting: mypy pylint

mypy:
	mypy --strict app

pylint:
	find app -name *.py | xargs pylint

test:
	pytest -v ./app/tests
