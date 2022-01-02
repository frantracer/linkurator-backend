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
	python3.8 -m pip install virtualenv
	python3.8 -m venv venv
	@echo
	@echo "Run 'source venv/bin/activate' before any other make command"
	@echo "Run 'deactivate' to disable the virtual environment"

setup:
	pip3 install -r requirements.txt

run:
	python3.8 src

dev-run:
	python3.8 src --reload --workers 1 --debug

check-linting: mypy pylint

mypy:
	mypy --config-file mypy.ini src tests

pylint:
	find src tests -name *.py | xargs pylint --rcfile=.pylintrc

test:
	pytest -v ./tests
