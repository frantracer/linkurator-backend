FROM python:3.10

RUN apt update  \
    && apt install -y ansible \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./linkurator_core ./linkurator_core
COPY scripts ./scripts
COPY ./tests ./tests
COPY ./requirements.txt ./requirements.txt
COPY ./pyproject.toml ./pyproject.toml
COPY ./.pylintrc ./.pylintrc
COPY ./pytest.ini ./pytest.ini
COPY ./Makefile ./Makefile
COPY ./config ./config

RUN make install

EXPOSE 9000

CMD ["make", "run"]
