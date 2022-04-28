SHELL := /bin/bash

DOCKER_IMAGE := frantracer/linkurator-api
DOCKER_CONTAINER_APP := linkurator-api
DOCKER_CONTAINER_LINTING := linkurator-api-check-linting
DOCKER_CONTAINER_TEST := linkurator-test

docker-build:
	docker rmi -f $(DOCKER_IMAGE)
	docker build -t $(DOCKER_IMAGE) .

docker-push:
	docker push $(DOCKER_IMAGE)

docker-run: check-vault-pass-is-defined
	@docker rm -f $(DOCKER_CONTAINER_APP)
	@docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		--name $(DOCKER_CONTAINER_APP) --network host -d $(DOCKER_IMAGE)

docker-stop:
	docker stop $(DOCKER_CONTAINER_APP)

docker-check-linting:
	docker rm -f $(DOCKER_CONTAINER_LINTING)
	docker run --name $(DOCKER_CONTAINER_LINTING) --network host $(DOCKER_IMAGE) make check-linting

docker-run-external-services:
	docker-compose up -d

docker-test: docker-run-external-services
	docker rm -f $(DOCKER_CONTAINER_TEST)
	docker run --name $(DOCKER_CONTAINER_TEST) --network host $(DOCKER_IMAGE) make test

deploy: check-vault-pass-is-defined check-ssh-connection
	ssh root@$(SSH_IP_ADDRESS) "docker stop $(DOCKER_CONTAINER_APP)"
	ssh root@$(SSH_IP_ADDRESS) "docker rm $(DOCKER_CONTAINER_APP)"
	ssh root@$(SSH_IP_ADDRESS) "docker pull $(DOCKER_IMAGE)"
	@ssh root@$(SSH_IP_ADDRESS) "docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		--name $(DOCKER_CONTAINER_APP) --network host -d $(DOCKER_IMAGE)"
	ssh root@$(SSH_IP_ADDRESS) "docker image prune -a -f"
	@echo "Latest image is deployed"

setup:
	python3.8 -m pip install virtualenv
	rm -rf venv
	python3.8 -m venv venv
	./venv/bin/pip3 install -r requirements.txt
	@echo
	@echo "Run 'source venv/bin/activate' to activate the virtual environment."
	@echo "Run 'deactivate' to disable the virtual environment."

install-python:
	apt install -y python3.8-venv python3-pip

check-vault-pass-is-defined:
	@if [ -z "${LINKURATOR_VAULT_PASSWORD}" ]; then echo "LINKURATOR_VAULT_PASSWORD environment variable is not set"; exit 1; fi

check-ssh-connection:
	@if [ -z "${SSH_IP_ADDRESS}" ]; then echo "SSH_IP_ADDRESS environment variable is not set"; exit 1; fi
	@ssh root@$(SSH_IP_ADDRESS) "echo Connection OK"

encrypt-secrets: create-vault-pass
	cp secrets/client_secret.json config/client_secret.json.enc
	ansible-vault encrypt --vault-password-file=secrets/vault_password.txt config/client_secret.json.enc

decrypt-secrets: create-vault-pass
	cp config/client_secret.json.enc secrets/client_secret.json
	ansible-vault decrypt --vault-password-file=secrets/vault_password.txt secrets/client_secret.json

create-vault-pass: check-vault-pass-is-defined
	@mkdir -p secrets
	@echo -n $(LINKURATOR_VAULT_PASSWORD) > secrets/vault_password.txt
	@echo "Vault password stored in secrets/vault_password.txt"

run: decrypt-secrets
	./venv/bin/python3.8 -m linkurator_core

dev-run: decrypt-secrets
	./venv/bin/python3.8 -m linkurator_core --reload --workers 1 --debug --without-gunicorn

check-linting: mypy pylint

mypy:
	./venv/bin/mypy --config-file mypy.ini linkurator_core tests

pylint:
	find ./linkurator_core -name '*.py' | xargs ./venv/bin/pylint --rcfile=.pylintrc
	find ./tests -name '*.py' | xargs ./venv/bin/pylint --rcfile=.pylintrc

test:
	./venv/bin/pytest -v tests
