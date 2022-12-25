# Introduction

Linkurator API allows you to explore and categorise your YouTube subscriptions.

The API is currently available at https://api.linkurator.com/docs

# Setup

## Requirements

* Python 3.8 with pip and venv
* Docker
* Docker Compose
* Ansible vault password to decrypt some secrets

The requirements can be installed with: 
```bash
make install-requirements
```

## Installation

1. Install the dependencies with:
```bash
make install
make docker-run-external-services
```

2. Get the ansible vault password and store in the secrets folder
```bash
echo "YOUR_PASSWORD" > secrets/vault_password.txt
export LINKURATOR_VAULT_PASSWORD=$(cat secrets/vault_password.txt)
```

3. Select the environment with:
```bash
export LINKURATOR_ENVIRONMENT=DEVELOPMENT
```

Available environments are:
* DEVELOPMENT
* PRODUCTION

# Run

The project is composed of two services: the API and the processor:
* The API allows you to explore your subscriptions
* The processor is in charge of fetching the data from YouTube.

## API

Run the API with your local python venv:
```bash
make run-api
```

Or with docker:
```bash
make docker-build
make docker-run-api
```

Once you have the API running, you can access the documentation at http://localhost:9000/docs

## Processor

Run the processor with your local python venv:
```bash
make run-procesor
```

Or with docker:
```bash
make docker-build
make docker-run-processor
```

# First steps

1. Use your web browser to access to the login page: http://localhost:9000/login
2. Login with your Google account
3. The processor must be running in order to download the data from your subscriptions
4. You can use the API docs to explore your subscriptions: http://localhost:9000/docs


# Test

## Integration and unit tests

Run the tests with your local python venv:
```bash
make test
```

Or with docker:
```bash
make docker-build
make docker-test
```

## Lint

Run the linter with your local python venv:
```bash
make lint
```

Or with docker:
```bash
make docker-build
make docker-lint
```

# Deploy

Define the ip of the server to provision and deploy:
```bash
export SSH_IP_ADDRESS=api.linkurator.com
```

Define the ansible vault password:
```bash
export LINKURATOR_VAULT_PASSWORD=$(cat secrets/vault_password.txt)
```

Then you need to provision a server with docker.
```bash
make provision
```

Once the server is provisioned, you can deploy the application with:
```bash
make docker-build
make docker-push
make deploy
```

## Continuous Deployment

Every push to the master branch will trigger the tests and the linting. If they pass, the application will be automatically deployed to the server.
