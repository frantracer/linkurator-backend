FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt update  \
    && apt install -y make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./linkurator_core ./linkurator_core
COPY scripts ./scripts
COPY ./tests ./tests
COPY ./requirements.txt ./requirements.txt
COPY ./pyproject.toml ./pyproject.toml
COPY ./pytest.ini ./pytest.ini
COPY ./Makefile ./Makefile
COPY ./config ./config

RUN make install

EXPOSE 9000

CMD ["make", "run"]
