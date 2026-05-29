SHELL := /bin/bash

DOMAIN := api.linkurator.com

DOCKER_IMAGE := frantracer/linkurator-api
DOCKER_CONTAINER_API := linkurator-api
DOCKER_CONTAINER_PROCESSOR := linkurator-processor
DOCKER_CONTAINER_LINTING := linkurator-api-check-linting
DOCKER_CONTAINER_TEST := linkurator-test

COMPOSE_FILE := docker-compose.yml
REMOTE_DEPLOY_DIR := /opt/linkurator
SSH_USER := root
SSH_TARGET := $(SSH_USER)@$(SSH_IP_ADDRESS)

-include .env
export

####################
# Run
####################
install-requirements:
	ARCH=$$(dpkg --print-architecture); \
	RELEASE=$$(lsb_release -cs); \
	sudo mkdir -p /etc/apt/keyrings && \
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
	echo "deb [arch=$$ARCH signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $$RELEASE stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && \
	sudo apt-get update

	sudo apt-get remove docker docker-engine docker.io containerd runc
	sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

	sudo usermod -aG docker ${USER}

	curl -LsSf https://astral.sh/uv/install.sh | sh

	@echo "Installation complete. Please restart your computer."

install:
	rm -rf .venv
	uv venv --python=python3.13.5 .venv
	uv pip install pip --upgrade
	uv pip install -r requirements.txt
	@echo
	@echo "Run 'source .venv/bin/activate' to activate the virtual environment."
	@echo "Run 'deactivate' to disable the virtual environment."

run-api-dev:
	.venv/bin/python3 -m linkurator_core --reload --workers 1 --debug --without-gunicorn;

run-api:
	.venv/bin/python3 -m linkurator_core;

run-processor:
	PYTHONPATH='.' .venv/bin/python3 ./linkurator_core/processor.py

generate-env-production: decrypt-secrets
	cp secrets/app_config_production.json .config.json
	PYTHONPATH='.' .venv/bin/python3 ./scripts/generate_env.py

generate-env-development:
	@if [ ! -f .config.json ]; then cp config/app_config_develop.json .config.json; fi
	PYTHONPATH='.' .venv/bin/python3 ./scripts/generate_env.py

generate-env:
	@if [ -z "${LINKURATOR_ENVIRONMENT}" ]; then \
		echo "LINKURATOR_ENVIRONMENT environment variable is not set. Please set it to either 'PRODUCTION' or 'DEVELOPMENT'."; \
		exit 1; \
	fi
	@if [ "${LINKURATOR_ENVIRONMENT}" = "PRODUCTION" ]; then \
		$(MAKE) generate-env-production; \
	elif [ "${LINKURATOR_ENVIRONMENT}" = "DEVELOPMENT" ]; then \
		$(MAKE) generate-env-development; \
	else \
		echo "Invalid LINKURATOR_ENVIRONMENT value. Please set it to either 'PRODUCTION' or 'DEVELOPMENT'."; \
		exit 1; \
	fi

####################
# Setup configuration
####################

check-password:
	@if [ -z "${LINKURATOR_VAULT_PASSWORD}" ]; then \
		echo "LINKURATOR_VAULT_PASSWORD environment variable is not set"; \
		exit 1; \
	fi

encrypt-secrets: check-password
	rm -rf config/*.enc
	.venv/bin/python3 scripts/encrypt_decrypt.py encrypt secrets/app_config_production.json config/app_config_production.json.enc

decrypt-secrets: check-password
	mkdir -p secrets
	.venv/bin/python3 scripts/encrypt_decrypt.py decrypt config/app_config_production.json.enc secrets/app_config_production.json

####################
# Test
####################
lint: mypy ruff

mypy:
	.venv/bin/mypy --config-file pyproject.toml linkurator_core tests scripts

ruff:
	.venv/bin/ruff check linkurator_core tests scripts

format:
	.venv/bin/ruff check linkurator_core tests scripts --fix

test:
	.venv/bin/coverage run -m pytest -v tests
	.venv/bin/coverage xml
	.venv/bin/coverage report --fail-under 91

####################
# Docker
####################
docker-build:
	docker rmi -f $(DOCKER_IMAGE)
	docker build -q -t $(DOCKER_IMAGE) .

docker-run-api:
	docker compose --profile app --profile infra up -d --force-recreate api

docker-run-processor:
	docker compose --profile app --profile infra up -d --force-recreate processor

docker-test: docker-run-external-services
	docker rm -f $(DOCKER_CONTAINER_TEST)
	docker run --name $(DOCKER_CONTAINER_TEST) --pull never --network host $(DOCKER_IMAGE) make test

docker-lint:
	docker rm -f $(DOCKER_CONTAINER_LINTING)
	docker run --name $(DOCKER_CONTAINER_LINTING) --pull never --network host $(DOCKER_IMAGE) make lint

docker-generate-env: docker-build
	docker compose --profile init run --rm generate-env

docker-up: docker-generate-env
	docker compose --profile app --profile infra up -d

docker-run-external-services:
	docker compose --profile infra up -d --quiet-pull

docker-stop:
	docker compose --profile app --profile infra stop

check-docker-token:
	@if [ -z "${LINKURATOR_DOCKER_TOKEN}" ]; then \
		echo "LINKURATOR_DOCKER_TOKEN environment variable is not set"; \
		exit 1; \
	fi

docker-push: check-docker-token
	@docker login -u frantracer -p ${LINKURATOR_DOCKER_TOKEN}
	docker push $(DOCKER_IMAGE)

####################
# Provision
####################
check-ssh-connection:
	@if [ -z "${SSH_IP_ADDRESS}" ]; then echo "SSH_IP_ADDRESS environment variable is not set"; exit 1; fi
	@ssh $(SSH_TARGET) "echo Connection OK"

provision: check-ssh-connection
	@echo "Provisioning"
	@ssh $(SSH_TARGET) "apt update && apt install -y docker.io nginx certbot python3-certbot-nginx"
	@scp config/docker_daemon.json $(SSH_TARGET):/etc/docker/daemon.json
	@ssh $(SSH_TARGET) "systemctl restart docker"
	@ssh $(SSH_TARGET) "rm -rf /etc/nginx/sites-enabled/default"
	@scp config/linkurator-api.conf $(SSH_TARGET):/etc/nginx/sites-enabled/linkurator-api.conf
	@ssh $(SSH_TARGET) "certbot --nginx -d $(DOMAIN) -n --redirect"
	@ssh $(SSH_TARGET) "systemctl restart nginx"
	@ssh $(SSH_TARGET) "apt autoremove -y"

# Generate the deploy SSH keypair, authorize it on the host and print every
# secret the cd.yml pipeline expects so they can be pasted into GitHub:
# Settings > Environments > Production > Add secret.
create-deploy-credentials: check-ssh-connection
	@mkdir -p secrets
	@if [ ! -f secrets/deploy_key ]; then \
		ssh-keygen -t ed25519 -C "github-cd-linkurator" -f secrets/deploy_key -N ""; \
	else \
		echo "secrets/deploy_key already exists, reusing it"; \
	fi
	@echo "Authorizing public key on $(SSH_TARGET)"
	@ssh $(SSH_TARGET) "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
	@cat secrets/deploy_key.pub | ssh $(SSH_TARGET) "cat >> ~/.ssh/authorized_keys && sort -u -o ~/.ssh/authorized_keys ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
	@ssh-keyscan -H $(SSH_IP_ADDRESS) > secrets/known_hosts 2>/dev/null
	@echo ""
	@echo "==================================================================="
	@echo "Paste these into GitHub > Settings > Environments > Production"
	@echo "==================================================================="
	@echo ""
	@echo "------- SSH_PRIVATE_KEY -------"
	@cat secrets/deploy_key
	@echo "------- SSH_KNOWN_HOSTS -------"
	@cat secrets/known_hosts
	@echo "------- PRODUCTION_IP_ADDRESS -------"
	@echo "$(SSH_IP_ADDRESS)"
	@echo "------- LINKURATOR_VAULT_PASSWORD -------"
	@if [ -n "$${LINKURATOR_VAULT_PASSWORD}" ]; then printf '%s\n' "$${LINKURATOR_VAULT_PASSWORD}"; else echo "(not set - export LINKURATOR_VAULT_PASSWORD and re-run)"; fi
	@echo "------- LINKURATOR_DOCKER_TOKEN -------"
	@if [ -n "$${LINKURATOR_DOCKER_TOKEN}" ]; then printf '%s\n' "$${LINKURATOR_DOCKER_TOKEN}"; else echo "(not set - create at hub.docker.com/settings/security, export LINKURATOR_DOCKER_TOKEN and re-run)"; fi
	@echo ""
	@echo "==================================================================="

####################
# Deploy
####################
check-env-file:
	@if [ ! -f .env ]; then \
		echo ".env file not found. Run 'make docker-generate-env' first."; \
		exit 1; \
	fi

remote-compose = ssh $(SSH_TARGET) "cd $(REMOTE_DEPLOY_DIR) && docker compose -f $(COMPOSE_FILE) $(1)"

remote-generate-env = printf '%s\n' "$$LINKURATOR_VAULT_PASSWORD" "$$LINKURATOR_ENVIRONMENT" | \
	ssh $(SSH_TARGET) "cd $(REMOTE_DEPLOY_DIR) \
	&& IFS= read -r LINKURATOR_VAULT_PASSWORD \
	&& IFS= read -r LINKURATOR_ENVIRONMENT \
	&& export LINKURATOR_VAULT_PASSWORD LINKURATOR_ENVIRONMENT \
	&& docker compose -f $(COMPOSE_FILE) --profile init run --rm -T generate-env"

push-deploy-files: check-ssh-connection check-password
	@ssh $(SSH_TARGET) "mkdir -p $(REMOTE_DEPLOY_DIR)"
	scp $(COMPOSE_FILE) $(SSH_TARGET):$(REMOTE_DEPLOY_DIR)/$(COMPOSE_FILE)
	$(call remote-compose,--profile app pull -q)
	@$(remote-generate-env)

deploy: push-deploy-files
	$(call remote-compose,--profile app up -d --force-recreate api processor)
	ssh $(SSH_TARGET) "docker image prune -a -f"
	@echo "Latest image is deployed"

deploy-infra: push-deploy-files
	$(call remote-compose,--profile infra up -d)

deploy-db: push-deploy-files
	$(call remote-compose,--profile infra up -d db)

deploy-queue: push-deploy-files
	$(call remote-compose,--profile infra up -d queue)

deploy-vpn: push-deploy-files
	$(call remote-compose, --profile infra up -d vpn)

deploy-down: check-ssh-connection
	$(call remote-compose,--profile app --profile infra down)

tunnel-rabbitmq: check-ssh-connection
	ssh -L 15000:localhost:15672 -N $(SSH_TARGET)
