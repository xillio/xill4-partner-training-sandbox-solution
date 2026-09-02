#!/usr/bin/env bash
# Provision one trainee's workspace for one scenario.
#
#   ./workspace/provision.sh alice 01-legacy-fileshare
#
# Idempotent per (trainee, scenario): re-running reseeds the source data and discards the
# trainee's target, which is exactly what "reset my sandbox" should do.
set -euo pipefail

TRAINEE="${1:?usage: provision.sh <trainee> [scenario]}"
SCENARIO="${2:-01-legacy-fileshare}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR=".workspaces/${TRAINEE}/${SCENARIO}"
WORKSPACE="${REPO_ROOT}/${WORKSPACE_DIR}"

if [[ ! -d "${REPO_ROOT}/scenarios/${SCENARIO}" ]]; then
  echo "no such scenario: ${SCENARIO}" >&2
  exit 1
fi

# A stable per-trainee port keeps a persistent workspace reachable at the same URL for the
# length of a course. 100 trainees per host is far beyond the cohort sizes we design for.
OFFSET=$(( 10#$(printf '%s' "${TRAINEE}" | cksum | cut -d' ' -f1) % 100 ))

mkdir -p "${WORKSPACE}"
python3 "${REPO_ROOT}/scenarios/${SCENARIO}/seedgen.py" \
  --workspace "${WORKSPACE}" --seed "${TRAINEE}:${SCENARIO}" --force

cat > "${REPO_ROOT}/workspace/.env" <<ENV
TRAINEE=${TRAINEE}
WORKSPACE_DIR=${WORKSPACE_DIR}
SCENARIO=${SCENARIO}
XILL4_IMAGE=${XILL4_IMAGE:-ghcr.io/xillio/xill4:PLACEHOLDER}
XILL4_PORT=$(( 8100 + OFFSET ))
XILL4_LICENCE=${XILL4_LICENCE:-}
MINIO_PORT=$(( 9100 + OFFSET ))
S3_ACCESS_KEY=trainee
S3_SECRET_KEY=trainee-secret
ENV

echo "workspace ready: ${WORKSPACE}"
echo "Xill4 will listen on http://localhost:$(( 8100 + OFFSET ))"
echo "next: (cd workspace && docker compose up -d)"
echo "grade with: make grade WORKSPACE=${WORKSPACE_DIR} SCENARIO=scenarios/${SCENARIO}"
