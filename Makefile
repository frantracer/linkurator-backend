SHELL := /bin/bash

docker-build:
	docker rmi -f linkurator-api
	docker build -t linkurator-api .

docker-run:
	docker rm -f linkurator-api
	docker run --name linkurator-api --network host -p 9000:9000 -d linkurator-api

docker-check-linting:
	docker rm -f linkurator-api-check-linting
	docker run --name linkurator-api-check-linting --network host linkurator-api make check-linting

docker-run-external-services:
	docker-compose up -d

docker-test: docker-run-external-services
	docker rm -f linkurator-api-test
	docker run --name linkurator-api-test --network host linkurator-api make test

setup:
	sudo apt install -y python3.8-venv python3-pip
	python3.8 -m pip install virtualenv
	python3.8 -m venv venv
	./venv/bin/pip3 install -r requirements.txt
	@echo
	@echo "Run 'source venv/bin/activate' to activate the virtual environment."
	@echo "Run 'deactivate' to disable the virtual environment."

run:
	./venv/bin/python3.8 -m linkurator_core

dev-run:
	./venv/bin/python3.8 -m linkurator_core --reload --workers 1 --debug

check-linting: mypy pylint

mypy:
	./venv/bin/mypy --config-file mypy.ini linkurator_core tests

pylint:
	find ./linkurator_core -name '*.py' | xargs pylint --rcfile=.pylintrc
	find ./tests -name '*.py' | xargs pylint --rcfile=.pylintrc

test:
	./venv/bin/pytest -v tests
