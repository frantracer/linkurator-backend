SHELL := /bin/bash

DOMAIN := api.linkurator.com

DOCKER_IMAGE := frantracer/linkurator-api
DOCKER_CONTAINER_API := linkurator-api
DOCKER_CONTAINER_PROCESSOR := linkurator-processor
DOCKER_CONTAINER_LINTING := linkurator-api-check-linting
DOCKER_CONTAINER_TEST := linkurator-test

####################
# Run
####################
ARCH := $(shell dpkg --print-architecture)
RELEASE := $(shell lsb_release -cs)
install-requirements:
	sudo mkdir -p /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
	echo "deb [arch=$(ARCH) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(RELEASE) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
	sudo apt-get update

	sudo apt-get remove docker docker-engine docker.io containerd runc
	sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

	sudo apt install -y python3.10-venv python3-pip

install:
	python3.10 -m pip install uv
	rm -rf .venv
	uv venv --python=python3.10 .venv
	uv pip install -r requirements.txt
	@echo
	@echo "Run 'source .venv/bin/activate' to activate the virtual environment."
	@echo "Run 'deactivate' to disable the virtual environment."

run-api: link-config
	@if [ "${LINKURATOR_ENVIRONMENT}" = "DEVELOPMENT" ]; then \
    	.venv/bin/python3.10 -m linkurator_core --reload --workers 1 --debug --without-gunicorn; \
	else \
		.venv/bin/python3.10 -m linkurator_core; \
	fi

run-processor: link-config
	PYTHONPATH='.' .venv/bin/python3.10 ./linkurator_core/processor.py

local-run-api: docker-run-external-services
	LINKURATOR_VAULT_PASSWORD=$(cat ./secrets/vault_password.txt) LINKURATOR_ENVIRONMENT=DEVELOPMENT \
		.venv/bin/python3.10 -m linkurator_core --reload --workers 1 --debug --without-gunicorn

local-run-processor: docker-run-external-services
	PYTHONPATH='.' LINKURATOR_VAULT_PASSWORD=$(cat ./secrets/vault_password.txt) LINKURATOR_ENVIRONMENT=DEVELOPMENT \
		.venv/bin/python3.10 ./linkurator_core/processor.py

####################
# Setup configuration
####################
check-vault-pass-is-defined:
	@if [ -z "${LINKURATOR_VAULT_PASSWORD}" ]; then echo "LINKURATOR_VAULT_PASSWORD environment variable is not set"; exit 1; fi

encrypt-secrets: create-vault-pass
	rm -f config/*.enc
	cp secrets/client_secret.json config/client_secret.json.enc
	cp secrets/app_config_production.ini config/app_config_production.ini.enc
	cp secrets/docker_token.txt config/docker_token.txt.enc
	cp secrets/google_api_key.txt config/google_api_key.txt.enc
	cp secrets/domain_service_credentials.json config/domain_service_credentials.json.enc
	cp secrets/spotify_credentials.json config/spotify_credentials.json.enc

	ansible-vault encrypt --vault-password-file=secrets/vault_password.txt config/*.enc

decrypt-secrets: create-vault-pass
	cp config/*.enc secrets/
	ansible-vault decrypt --vault-password-file=secrets/vault_password.txt secrets/*.enc

	mv -f secrets/client_secret.json.enc secrets/client_secret.json
	mv -f secrets/app_config_production.ini.enc secrets/app_config_production.ini
	mv -f secrets/docker_token.txt.enc secrets/docker_token.txt
	mv -f secrets/google_api_key.txt.enc secrets/google_api_key.txt
	mv -f secrets/domain_service_credentials.json.enc secrets/domain_service_credentials.json
	mv -f secrets/spotify_credentials.json.enc secrets/spotify_credentials.json

link-config:
	@if [ "${LINKURATOR_ENVIRONMENT}" = "PRODUCTION" ]; then \
		make link-prod-config; \
	elif [ "${LINKURATOR_ENVIRONMENT}" = "DEVELOPMENT" ]; then \
		make link-dev-config; \
	else \
		echo "LINKURATOR_ENVIRONMENT environment variable must be set to PRODUCTION or DEVELOPMENT"; \
		exit 1; \
	fi

link-dev-config: decrypt-secrets
	ln -sfn ../config/app_config_develop.ini secrets/app_config.ini

link-prod-config: decrypt-secrets
	ln -sfn app_config_production.ini secrets/app_config.ini

create-vault-pass: check-vault-pass-is-defined
	@mkdir -p secrets
	@echo -n $(LINKURATOR_VAULT_PASSWORD) > secrets/vault_password.txt
	@echo "Vault password stored in secrets/vault_password.txt"

####################
# Test
####################
lint: mypy pylint

mypy:
	.venv/bin/mypy --config-file pyproject.toml linkurator_core tests scripts

pylint:
	find ./linkurator_core -name '*.py' | xargs .venv/bin/pylint --rcfile=.pylintrc
	find ./tests -name '*.py' | xargs .venv/bin/pylint --rcfile=.pylintrc
	find ./scripts -name '*.py' | xargs .venv/bin/pylint --rcfile=.pylintrc

test:
	.venv/bin/coverage run -m pytest -v tests
	.venv/bin/coverage xml
	.venv/bin/coverage report --fail-under 90

####################
# Docker
####################
docker-build:
	docker rmi -f $(DOCKER_IMAGE)
	docker build -t $(DOCKER_IMAGE) .

docker-run-api: check-vault-pass-is-defined
	@docker rm -f $(DOCKER_CONTAINER_API)
	@docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		-e 'LINKURATOR_ENVIRONMENT=$(LINKURATOR_ENVIRONMENT)'\
		--pull never \
		--name $(DOCKER_CONTAINER_API) --network host -d $(DOCKER_IMAGE) make run-api

docker-run-processor: check-vault-pass-is-defined
	@docker rm -f $(DOCKER_CONTAINER_PROCESSOR)
	@docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		-e 'LINKURATOR_ENVIRONMENT=$(LINKURATOR_ENVIRONMENT)'\
		--pull never \
		--name $(DOCKER_CONTAINER_PROCESSOR) --network host -d $(DOCKER_IMAGE) make run-processor

docker-test: docker-run-external-services
	docker rm -f $(DOCKER_CONTAINER_TEST)
	docker run --name $(DOCKER_CONTAINER_TEST) --pull never --network host $(DOCKER_IMAGE) make test

docker-lint:
	docker rm -f $(DOCKER_CONTAINER_LINTING)
	docker run --name $(DOCKER_CONTAINER_LINTING) --pull never --network host $(DOCKER_IMAGE) make lint

docker-run-external-services:
	docker compose up -d

docker-stop:
	docker stop $(DOCKER_CONTAINER_API) $(DOCKER_CONTAINER_PROCESSOR)

docker-push: decrypt-secrets
	@docker login -u frantracer -p $(shell cat ./secrets/docker_token.txt)
	docker push $(DOCKER_IMAGE)

####################
# Provision
####################
check-ssh-connection:
	@if [ -z "${SSH_IP_ADDRESS}" ]; then echo "SSH_IP_ADDRESS environment variable is not set"; exit 1; fi
	@ssh root@$(SSH_IP_ADDRESS) "echo Connection OK"

provision: check-ssh-connection
	@echo "Provisioning"
	@ssh root@$(SSH_IP_ADDRESS) "apt update && apt install -y docker.io nginx certbot python3-certbot-nginx"
	@scp config/docker_daemon.json root@$(SSH_IP_ADDRESS):/etc/docker/daemon.json
	@ssh root@$(SSH_IP_ADDRESS) "systemctl restart docker"
	@ssh root@$(SSH_IP_ADDRESS) "rm -rf /etc/nginx/sites-enabled/default"
	@scp config/linkurator-api.conf root@$(SSH_IP_ADDRESS):/etc/nginx/sites-enabled/linkurator-api.conf
	@ssh root@$(SSH_IP_ADDRESS) "certbot --nginx -d $(DOMAIN) -n --redirect"
	@ssh root@$(SSH_IP_ADDRESS) "systemctl restart nginx"
	@ssh root@$(SSH_IP_ADDRESS) "apt autoremove -y"

####################
# Deploy
####################
deploy: check-vault-pass-is-defined check-ssh-connection
	ssh root@$(SSH_IP_ADDRESS) "docker pull $(DOCKER_IMAGE)"
	ssh root@$(SSH_IP_ADDRESS) "docker rm -f $(DOCKER_CONTAINER_API) $(DOCKER_CONTAINER_PROCESSOR)"
	@ssh root@$(SSH_IP_ADDRESS) "docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		-e 'LINKURATOR_ENVIRONMENT=PRODUCTION' --name $(DOCKER_CONTAINER_API) --network host --restart always \
		-d $(DOCKER_IMAGE) \
		make run-api"
	@ssh root@$(SSH_IP_ADDRESS) "docker run -e 'LINKURATOR_VAULT_PASSWORD=$(LINKURATOR_VAULT_PASSWORD)' \
		-e 'LINKURATOR_ENVIRONMENT=PRODUCTION' --name $(DOCKER_CONTAINER_PROCESSOR) --network host --restart always \
		-d $(DOCKER_IMAGE) \
		make run-processor"
	ssh root@$(SSH_IP_ADDRESS) "docker image prune -a -f"
	@echo "Latest image is deployed"

deploy-infra: deploy-mongodb deploy-rabbitmq

deploy-mongodb: check-ssh-connection
	@if [ -z "${MONGODB_USER}" ]; then echo "MONGODB_USER environment variable is not set"; exit 1; fi
	@if [ -z "${MONGODB_PASS}" ]; then echo "MONGODB_PASS environment variable is not set"; exit 1; fi

	ssh root@$(SSH_IP_ADDRESS) "docker run -d -p 27017:27017 --name linkurator-db --restart always -e 'MONGO_INITDB_ROOT_USERNAME=$(MONGODB_USER)' -e 'MONGO_INITDB_ROOT_PASSWORD=$(MONGODB_PASS)' mongo:5.0.5"

deploy-rabbitmq: check-ssh-connection
	@if [ -z "${RABBITMQ_USER}" ]; then echo "RABBITMQ_USER environment variable is not set"; exit 1; fi
	@if [ -z "${RABBITMQ_PASS}" ]; then echo "RABBITMQ_PASS environment variable is not set"; exit 1; fi

	ssh root@$(SSH_IP_ADDRESS) "docker run -d -p 5672:5672 -p 15672:15672 -h linkurator-rabbitmq --name linkurator-rabbitmq --restart always -e 'RABBITMQ_DEFAULT_USER=$(RABBITMQ_USER)' -e 'RABBITMQ_DEFAULT_PASS=$(RABBITMQ_PASS)' rabbitmq:3.13.0-management"

tunnel-rabbitmq: check-ssh-connection
	ssh -L 15000:localhost:15672 -N root@$(SSH_IP_ADDRESS)
