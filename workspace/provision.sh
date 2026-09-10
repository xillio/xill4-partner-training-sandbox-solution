#!/usr/bin/env bash
# Provision one trainee's sandbox: their workspace directory and their database.
#
#   ./workspace/provision.sh alice 01-legacy-fileshare
#   ./workspace/provision.sh alice 01-legacy-fileshare --reset    # start over completely
#   ./workspace/provision.sh alice 01-legacy-fileshare --no-db    # grading only, no Xill4
#
# A trainee's state has two halves, because the Xill4 image keeps projects and flows in
# MongoDB rather than on disk:
#
#   the workspace directory   source/, target/ and the grader-only .expected/
#   the database              everything the trainee builds inside Xill4
#
# Re-running is idempotent: the source data is regenerated from the same seed (so it is
# byte-identical), the trainee's target is discarded, and their database is left alone.
# `--reset` drops the database too -- that is the difference between "give me a clean
# target" and "I want to start this scenario from nothing".
set -euo pipefail

usage() { echo "usage: provision.sh <trainee> [scenario] [--reset] [--no-db]" >&2; exit 1; }

TRAINEE=""; SCENARIO="01-legacy-fileshare"; RESET=0; WITH_DB=1
for arg in "$@"; do
  case "${arg}" in
    --reset) RESET=1 ;;
    --no-db) WITH_DB=0 ;;
    -*) usage ;;
    *) if [[ -z "${TRAINEE}" ]]; then TRAINEE="${arg}"; else SCENARIO="${arg}"; fi ;;
  esac
done
[[ -n "${TRAINEE}" ]] || usage

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR=".workspaces/${TRAINEE}/${SCENARIO}"
WORKSPACE="${REPO_ROOT}/${WORKSPACE_DIR}"
ENV_DIR="${REPO_ROOT}/workspace"
PLATFORM_ENV="${ENV_DIR}/.env.platform"
MONGO_CONTAINER="${MONGO_CONTAINER:-xill4-sbx-mongo}"

if [[ ! -d "${REPO_ROOT}/scenarios/${SCENARIO}" ]]; then
  echo "no such scenario: ${SCENARIO}" >&2
  exit 1
fi

# ---------------------------------------------------------------- deployment-wide config
# Generated once per host. The licence key is the one value a human has to supply; the
# secrets are generated here so that nobody is tempted to reuse a memorable one.
python3 "${ENV_DIR}/sandbox.py" init-platform-env --env-dir "${ENV_DIR}" >/dev/null
if ! grep -qE '^XILL4_LICENSE_KEY=.+' "${PLATFORM_ENV}"; then
  echo "note: XILL4_LICENSE_KEY is empty in ${PLATFORM_ENV##"${REPO_ROOT}"/}" >&2
  echo "      the workspace below is still usable for grading; Xill4 will not start without it" >&2
fi

# ------------------------------------------------------------------ the workspace half
mkdir -p "${WORKSPACE}"
python3 "${REPO_ROOT}/scenarios/${SCENARIO}/seedgen.py" \
  --workspace "${WORKSPACE}" --seed "${TRAINEE}:${SCENARIO}" --force

# The image runs as a fixed uid; a bind mount the host created as root is not writable by
# it, and a migration that cannot write lands nothing without saying so. XILL4_RUN_AS_UID
# comes from .env.platform, where preflight.py tells you to put it.
RUN_AS_UID="$(grep -E '^XILL4_RUN_AS_UID=' "${PLATFORM_ENV}" | cut -d= -f2- || true)"
python3 "${ENV_DIR}/sandbox.py" prepare-workspace --workspace "${WORKSPACE}" \
  --uid "${RUN_AS_UID:-}" | sed 's/^/permissions: /'

TRAINEE_ENV="$(python3 "${ENV_DIR}/sandbox.py" env-path --trainee "${TRAINEE}" --env-dir "${ENV_DIR}")"
# Rendered to a temporary file first: redirecting straight into the destination would
# truncate it before sandbox.py reads back the port and password it must carry forward.
RENDERED="$(mktemp)"
trap 'rm -f "${RENDERED}"' EXIT
python3 "${ENV_DIR}/sandbox.py" render-env \
  --trainee "${TRAINEE}" --scenario "${SCENARIO}" \
  --workspace-dir "${WORKSPACE_DIR}" --env-dir "${ENV_DIR}" > "${RENDERED}"
install -m 600 "${RENDERED}" "${TRAINEE_ENV}"

read_env() { grep -E "^$1=" "${TRAINEE_ENV}" | head -1 | cut -d= -f2-; }
XILL4_PORT="$(read_env XILL4_PORT)"
DB_NAME="$(read_env MONGO_DATABASE)"
DB_USER="$(read_env MONGO_USER)"
DB_PASSWORD="$(read_env MONGO_PASSWORD)"

# ------------------------------------------------------------------- the database half
if (( WITH_DB )); then
  if ! docker exec "${MONGO_CONTAINER}" mongosh --quiet --eval 'db.runCommand({ping:1}).ok' \
       >/dev/null 2>&1; then
    echo "cannot reach MongoDB in container '${MONGO_CONTAINER}'." >&2
    echo "  start it first:  make platform-up" >&2
    echo "  or, to provision the workspace for grading only:  $0 ${TRAINEE} ${SCENARIO} --no-db" >&2
    exit 1
  fi

  ROOT_USER="$(grep -E '^MONGO_ROOT_USER=' "${PLATFORM_ENV}" | cut -d= -f2-)"
  ROOT_PASSWORD="$(grep -E '^MONGO_ROOT_PASSWORD=' "${PLATFORM_ENV}" | cut -d= -f2-)"

  # Credentials go in as container environment rather than argv, so they do not sit in the
  # host's process list while this runs.
  docker exec \
    -e ROOT_USER="${ROOT_USER}" -e ROOT_PASSWORD="${ROOT_PASSWORD}" \
    -e DB_NAME="${DB_NAME}" -e DB_USER="${DB_USER}" -e DB_PASSWORD="${DB_PASSWORD}" \
    -e DROP="${RESET}" \
    "${MONGO_CONTAINER}" mongosh --quiet --eval '
      const env = process.env;
      if (!db.getSiblingDB("admin").auth(env.ROOT_USER, env.ROOT_PASSWORD)) {
        throw new Error("root authentication failed -- check MONGO_ROOT_PASSWORD");
      }
      const target = db.getSiblingDB(env.DB_NAME);
      if (env.DROP === "1") {
        target.dropDatabase();
        print("dropped database " + env.DB_NAME);
      }
      // dbOwner on their own database and nothing else: the trainee can read this
      // connection string out of their own container, and it is worth only their sandbox.
      const roles = [{role: "dbOwner", db: env.DB_NAME}];
      if (target.getUser(env.DB_USER)) {
        target.updateUser(env.DB_USER, {pwd: env.DB_PASSWORD, roles: roles});
        print("updated user " + env.DB_USER + " on " + env.DB_NAME);
      } else {
        target.createUser({user: env.DB_USER, pwd: env.DB_PASSWORD, roles: roles});
        print("created user " + env.DB_USER + " on " + env.DB_NAME);
      }
    '
else
  echo "skipping the database half (--no-db): workspace is provisioned for grading only"
fi

cat <<SUMMARY

workspace ready: ${WORKSPACE_DIR}
database:        ${DB_NAME} (user ${DB_USER})

next:
  cd workspace && docker compose --env-file .env.platform --env-file ${TRAINEE_ENV##*/} up -d
  open http://localhost:${XILL4_PORT}
  make grade WORKSPACE=${WORKSPACE_DIR} SCENARIO=scenarios/${SCENARIO}
SUMMARY
