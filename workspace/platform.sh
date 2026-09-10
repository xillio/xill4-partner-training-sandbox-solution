#!/usr/bin/env bash
# The shared half of the sandbox: the MongoDB every trainee's Xill4 keeps its projects and
# flows in. Brought up once per host, before any trainee stack.
#
#   ./workspace/platform.sh up                 start the shared MongoDB
#   ./workspace/platform.sh status             is it up, and which databases exist
#   ./workspace/platform.sh backup alice       dump one trainee's flows to backups/
#   ./workspace/platform.sh restore alice DIR  put them back
#   ./workspace/platform.sh down               stop it (data survives in the volume)
#
# Backup and restore are what make a multi-day course survivable: the trainee's work is not
# on a filesystem we can copy, it is in their database, so `mongodump` is the only thing
# standing between a host rebuild and a room full of lost work.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${REPO_ROOT}/workspace"
PLATFORM_ENV="${ENV_DIR}/.env.platform"
COMPOSE=(docker compose --env-file "${PLATFORM_ENV}" -f "${ENV_DIR}/docker-compose.platform.yml")
MONGO_CONTAINER="${MONGO_CONTAINER:-xill4-sbx-mongo}"
BACKUP_ROOT="${BACKUP_ROOT:-${REPO_ROOT}/.backups}"

python3 "${ENV_DIR}/sandbox.py" init-platform-env --env-dir "${ENV_DIR}" >/dev/null

root_user() { grep -E '^MONGO_ROOT_USER=' "${PLATFORM_ENV}" | cut -d= -f2-; }
root_password() { grep -E '^MONGO_ROOT_PASSWORD=' "${PLATFORM_ENV}" | cut -d= -f2-; }
# The database name comes from sandbox.py, never from string-building here: the
# provisioner and the backup must agree on which database is whose.
database_of() { python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import sandbox; \
                            print(sandbox.database_name(sys.argv[2]))" "${ENV_DIR}" "$1"; }

# Runs a mongosh snippet as root, with the credentials passed as container environment
# rather than argv so they stay out of the host's process list.
as_root() {
  docker exec -e ROOT_USER="$(root_user)" -e ROOT_PASSWORD="$(root_password)" "$@" \
    "${MONGO_CONTAINER}" mongosh --quiet --eval "
      if (!db.getSiblingDB('admin').auth(process.env.ROOT_USER, process.env.ROOT_PASSWORD)) {
        throw new Error('root authentication failed');
      }
      ${SNIPPET}"
}

case "${1:-}" in
  up)
    "${COMPOSE[@]}" up -d
    printf 'waiting for MongoDB'
    for _ in $(seq 1 30); do
      if docker exec "${MONGO_CONTAINER}" mongosh --quiet \
           --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1; then
        echo " ready"
        echo "next: ./workspace/provision.sh <trainee> <scenario>"
        exit 0
      fi
      printf '.'; sleep 2
    done
    echo " timed out; check: ${COMPOSE[*]} logs mongo" >&2
    exit 1
    ;;

  down)
    "${COMPOSE[@]}" down
    echo "stopped. Trainee data survives in the mongo-data volume; 'down -v' would destroy it."
    ;;

  status)
    "${COMPOSE[@]}" ps
    SNIPPET='printjson(db.getSiblingDB("admin").adminCommand({listDatabases: 1}).databases
               .filter(d => d.name.startsWith("xill4_"))
               .map(d => ({database: d.name, mb: +(d.sizeOnDisk / 1048576).toFixed(1)})));' \
      as_root || true
    ;;

  backup)
    TRAINEE="${2:?usage: platform.sh backup <trainee>}"
    DATABASE="$(database_of "${TRAINEE}")"
    DESTINATION="${BACKUP_ROOT}/${DATABASE}-$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "${DESTINATION}"
    docker exec -e ROOT_USER="$(root_user)" -e ROOT_PASSWORD="$(root_password)" \
      -e DATABASE="${DATABASE}" "${MONGO_CONTAINER}" \
      sh -c 'mongodump --quiet --username "$ROOT_USER" --password "$ROOT_PASSWORD" \
               --authenticationDatabase admin --db "$DATABASE" --archive' \
      > "${DESTINATION}/dump.archive"
    echo "backed up ${DATABASE} to ${DESTINATION}/dump.archive"
    ;;

  restore)
    TRAINEE="${2:?usage: platform.sh restore <trainee> <archive>}"
    ARCHIVE="${3:?usage: platform.sh restore <trainee> <archive>}"
    DATABASE="$(database_of "${TRAINEE}")"
    docker exec -i -e ROOT_USER="$(root_user)" -e ROOT_PASSWORD="$(root_password)" \
      "${MONGO_CONTAINER}" \
      sh -c 'mongorestore --quiet --username "$ROOT_USER" --password "$ROOT_PASSWORD" \
               --authenticationDatabase admin --drop --archive' < "${ARCHIVE}"
    echo "restored ${DATABASE} from ${ARCHIVE}"
    ;;

  *)
    echo "usage: platform.sh {up|down|status|backup <trainee>|restore <trainee> <archive>}" >&2
    exit 1
    ;;
esac
