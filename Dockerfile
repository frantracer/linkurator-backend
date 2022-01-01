FROM python:3.8

WORKDIR /app

COPY ./ ./

RUN make setup

EXPOSE 9000

CMD ["make", "run"]
