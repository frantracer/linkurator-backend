export FILE_NAME="linkurator_db_dump_$(date +%Y%m%d%H%M%S).archive"

docker exec linkurator-db mongodump --username develop --password develop --archive > $FILE_NAME

docker exec -i linkurator-db mongorestore --username develop --password develop --archive < $FILE_NAME
