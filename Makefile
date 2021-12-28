SHELL := /bin/bash

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

setup-venv:
	sudo apt install -y python3.8-venv python3-pip
	pip3 install virtualenv
	python3 -m venv venv

activate-venv:
	source venv/bin/activate

setup: activate-venv
	pip3 install -r requirements.txt

run: activate-venv
	cd app; uvicorn server:app --host 0.0.0.0 --port 9000

dev-run: activate-venv
	cd app; uvicorn server:app --reload --host 0.0.0.0 --port 9000

check-linting: mypy pylint

mypy: activate-venv
	mypy --strict app

pylint: activate-venv
	find app -name *.py | xargs pylint

test: activate-venv
	pytest -v ./app/tests
