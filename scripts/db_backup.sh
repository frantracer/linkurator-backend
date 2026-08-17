#!/usr/bin/env bash
# Usage:
#   db_backup.sh backup <env_file>
#   db_backup.sh restore <env_file> [backup_file_name]
# If no file name is given to restore, the most recent backup in the bucket is used.
set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ACTION="${1:-}"
ENV_FILE="${2:-}"

if [ "$ACTION" != "backup" ] && [ "$ACTION" != "restore" ]; then
  echo "Usage: $0 backup|restore <env_file> [backup_file_name]" >&2
  exit 1
fi

if [ -z "$ENV_FILE" ]; then
  echo "Usage: $0 backup|restore <env_file> [backup_file_name]" >&2
  exit 1
fi

log "Loading environment from $ENV_FILE"
set -a
source "$ENV_FILE"
set +a

REQUIRED_VARS=(POSTGRES_USER POSTGRES_PASS R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET R2_BACKUP_PATH)
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR:-}" ]; then
    echo "Missing required variable in $ENV_FILE: $VAR" >&2
    exit 1
  fi
done

# aws-cli reads these directly; exporting once here avoids repeating them on every call.
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"

R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
MAX_BACKUPS=5

# Normalize backup_path (e.g. "/develop") into a "develop/" key prefix so
# different environments sharing a bucket don't collide.
R2_PREFIX="${R2_BACKUP_PATH#/}"
R2_PREFIX="${R2_PREFIX%/}"
if [ -n "$R2_PREFIX" ]; then
  R2_PREFIX="${R2_PREFIX}/"
fi

if [ "$ACTION" = "backup" ]; then
  FILE_NAME="linkurator_db_dump_$(date +%Y%m%d%H%M%S).dump"
  KEY="${R2_PREFIX}${FILE_NAME}"

  log "Dumping database 'main' to $FILE_NAME"
  docker exec -e PGPASSWORD="$POSTGRES_PASS" linkurator-postgres \
    pg_dump --username "$POSTGRES_USER" --format custom --dbname main > "$FILE_NAME"

  log "Uploading backup to s3://${R2_BUCKET}/${KEY}"
  aws s3 cp "$FILE_NAME" "s3://${R2_BUCKET}/${KEY}" --endpoint-url "$R2_ENDPOINT"

  rm "$FILE_NAME"

  log "Backup uploaded: $KEY"

  log "Checking for old backups to prune (keeping last $MAX_BACKUPS)"
  EXISTING_FILES=$(aws s3 ls "s3://${R2_BUCKET}/${R2_PREFIX}" --endpoint-url "$R2_ENDPOINT" \
    | awk '{print $4}' | sort)

  OLD_FILES=$(echo "$EXISTING_FILES" | head -n -"$MAX_BACKUPS")

  if [ -z "$OLD_FILES" ]; then
    log "No old backups to prune"
  fi

  for OLD_FILE in $OLD_FILES; do
    OLD_KEY="${R2_PREFIX}${OLD_FILE}"
    aws s3 rm "s3://${R2_BUCKET}/${OLD_KEY}" --endpoint-url "$R2_ENDPOINT"

    log "Removed old backup: $OLD_KEY"
  done

  log "Backup complete"

elif [ "$ACTION" = "restore" ]; then
  FILE_NAME="${3:-}"

  if [ -z "$FILE_NAME" ]; then
    log "No backup file given; looking up the most recent backup in s3://${R2_BUCKET}/${R2_PREFIX}"
    FILE_NAME=$(aws s3 ls "s3://${R2_BUCKET}/${R2_PREFIX}" --endpoint-url "$R2_ENDPOINT" \
      | awk '{print $4}' | sort | tail -n 1)

    if [ -z "$FILE_NAME" ]; then
      echo "No backups found in s3://${R2_BUCKET}/${R2_PREFIX}" >&2
      exit 1
    fi
  fi

  KEY="${R2_PREFIX}${FILE_NAME}"
  LOCAL_FILE="$FILE_NAME"

  log "Downloading backup s3://${R2_BUCKET}/${KEY}"
  aws s3 cp "s3://${R2_BUCKET}/${KEY}" "$LOCAL_FILE" --endpoint-url "$R2_ENDPOINT"

  log "Restoring database 'main' from $LOCAL_FILE"
  # pg_restore exits 1 whenever it reports any ignored error, even harmless
  # "already exists"-style ones under --clean --if-exists, so it can't be
  # allowed to abort the script here.
  set +e
  docker exec -i -e PGPASSWORD="$POSTGRES_PASS" linkurator-postgres \
    pg_restore --username "$POSTGRES_USER" --clean --if-exists --no-owner --dbname main < "$LOCAL_FILE"
  RESTORE_STATUS=$?
  set -e

  if [ "$RESTORE_STATUS" -ne 0 ]; then
    echo "pg_restore reported errors (see above); reapplying full-text search objects as a safety net" >&2
    echo "(expected only for backups taken before the immutable_unaccent search_path fix)" >&2
  fi

  log "Reapplying full-text search objects (idempotent safety net)"
  # pg_dump/pg_restore always run with search_path='' for restore safety. Backups taken
  # before immutable_unaccent's body was schema-qualified fail to create these indexes
  # during restore for that reason; reapply them here (idempotent) so old backups still
  # restore into a working state. Safe to remove once no such backups remain in rotation.
  docker exec -i -e PGPASSWORD="$POSTGRES_PASS" linkurator-postgres \
    psql --username "$POSTGRES_USER" --dbname main -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text AS $$
    SELECT public.unaccent('public.unaccent', $1)
$$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;
CREATE INDEX IF NOT EXISTS items_name_search_idx ON items USING GIN (to_tsvector('simple', immutable_unaccent(name)));
CREATE INDEX IF NOT EXISTS subscriptions_name_search_idx ON subscriptions USING GIN (to_tsvector('simple', immutable_unaccent(name)));
CREATE INDEX IF NOT EXISTS topics_name_search_idx ON topics USING GIN (to_tsvector('simple', immutable_unaccent(name)));
SQL

  rm "$LOCAL_FILE"

  log "Restored from: $KEY"
fi
