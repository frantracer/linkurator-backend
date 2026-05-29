# 🔗 Introduction

Linkurator backend allows you to explore and categorize your subscriptions from various content providers like YouTube, Spotify, Patreon or RSS.

The API is currently available at https://api.linkurator.com/docs 📚

The project is composed of two app services and supporting infrastructure.

App services:
* 🌐 **api** — exposes the HTTP API used to explore your subscriptions.
* ⚙️ **processor** — fetches content from content providers in the background.

Infrastructure:
* **mongodb** and **rabbitmq** — required.
* **gluetun** — optional VPN.

# 🐳 Run with Docker (recommended)

### 📋 Requirements

* 🐳 docker and docker compose (https://docs.docker.com/engine/install/)

### 🚀 Quick start

Bring the whole stack up with a single command:

```bash
docker compose --profile init run --rm generate-env && \
docker compose --profile app --profile infra --profile vpn up -d
```

Once the API is running, the docs are at http://localhost:9000/docs. 📖

### 🛑 Stop

```bash
docker compose --profile app --profile infra --profile vpn stop
```

### ⚙️ Configuration

* `.config.json` is the source of truth for runtime settings
* `.env` is generated from `.config.json` and used by `docker compose`

# 👣 First steps

1. 🔐 Open the login page: http://localhost:9000/login
2. 👤 Log in with your Google account
3. ⚙️ The processor must be running to download subscription data
4. 📚 Explore via the API docs: http://localhost:9000/docs

# 🔨 Run with Make

### 📋 Requirements
* Make (for the convenience commands)

### ▶️ Run

Alternatively, build the image locally and bring everything up via Make:
```bash
make docker-up
```

### 🛑 Stop

```bash
make docker-stop
```

# 🐍 Run with Python venv

Use this path when you want hot-reload, a debugger, or to iterate on the app code without rebuilding the image.

Some infrastructure still runs in Docker.

### 📋 Requirements

* uv (for Python package management)
* Make (for the convenience commands)
* Docker (for the infrastructure containers)

### 🔧 Setup

1. Install the requirements
```bash
make install-requirements
```
Reboot is required after installing docker to run it without sudo.

2. Install python dependencies in a venv:
```bash
make install
```

3. Generate the `.env` file from `.config.json`:
```bash
make generate-env
```

### ▶️ Run

Start infrastructure containers:
```bash
make docker-run-external-services
```

Then each app service in a separate terminal:
```bash
make run-api
make run-processor
```

# 🧪 Test and lint

### 🐍 With Python venv

Run the tests:
```bash
make test
```

Run the linter:
```bash
make lint
```

Auto-fix formatting issues:
```bash
make format
```

### 🐳 With Docker

First build the image if you want to run tests in Docker:
```bash
make docker-build
```

Run the tests:
```bash
make docker-test
```

Run the linter:
```bash
make docker-lint
```

# 🖥️ Provision
Provision a server with Docker and deploy the app. This is the recommended way to run in production.

```bash
export SSH_IP_ADDRESS=api.linkurator.com
make provision
```

To allow the continuous deployment pipeline to deploy to the server run:
```bash
export SSH_IP_ADDRESS=api.linkurator.com
make create-deploy-credentials
```

# 🚢 Deploy

Build the docker images and push them to the registry:
```bash
make docker-build
make docker-push
```

`make docker-push` requires being authenticated to the Docker registry. If you
are not already logged in (`docker login`), set `LINKURATOR_DOCKER_TOKEN` to a
Docker Hub access token and the target will log in for you:
```bash
export LINKURATOR_DOCKER_TOKEN=your_docker_hub_token
```

Define the ip address and the vault password to deploy the image to the server:
```bash
echo "YOUR_PASSWORD" > secrets/vault_password.txt
export LINKURATOR_VAULT_PASSWORD=$(cat secrets/vault_password.txt)

export SSH_IP_ADDRESS=api.linkurator.com

export LINKURATOR_ENVIRONMENT=PRODUCTION

make deploy
```

`LINKURATOR_VAULT_PASSWORD` is needed because the production configuration
lives in `config/app_config_production.json.enc` (encrypted). When
`LINKURATOR_ENVIRONMENT=PRODUCTION`, the env-generation step decrypts that
file with the vault password before producing the `.env` shipped to the
server.

## 🔄 Continuous Deployment

Every push to the main branch will trigger the tests and the linting. If they pass, the application will be automatically deployed to the server.
