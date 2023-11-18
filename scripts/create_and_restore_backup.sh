docker exec -it linkurator-backend_mongodb_1 mongodump --username develop --password develop --archive=/backup/db_dump.archive

docker cp linkurator-backend_mongodb_1:/db_dump.archive .

docker-compose down

make docker-run-external-services

docker cp ./db_dump.archive linkurator-backend_mongodb_1:/db_dump.archive

docker exec -i linkurator-backend_mongodb_1 mongorestore --username develop --password develop --archive=/db_dump.archive
