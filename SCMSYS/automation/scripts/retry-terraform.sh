#!/usr/bin/env bash
set -euo pipefail

TF_DIR=${TF_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)}
INTERVAL=${INTERVAL:-60}
MAX_ATTEMPTS=${MAX_ATTEMPTS:-0}
LOG_FILE=${LOG_FILE:-"${TF_DIR}/last-apply.log"}
COUNT=0

cd "${TF_DIR}"

if [ ! -d .terraform ]; then
  echo "[setup] Running terraform init..."
  terraform init -input=false >/dev/null
fi

echo "[info] Starting retry loop in ${TF_DIR} (interval ${INTERVAL}s, max attempts ${MAX_ATTEMPTS:-∞})."

while true; do
  COUNT=$((COUNT + 1))
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "[${TIMESTAMP}] Attempt ${COUNT}: terraform apply -auto-approve"

  if terraform apply -auto-approve -input=false | tee "${LOG_FILE}"; then
    echo "[success] Apply completed on attempt ${COUNT}."
    break
  fi

  echo "[warn] Apply failed (likely capacity). See ${LOG_FILE} for details."

  if [ "${MAX_ATTEMPTS}" -gt 0 ] && [ "${COUNT}" -ge "${MAX_ATTEMPTS}" ]; then
    echo "[error] Giving up after ${COUNT} attempts."
    exit 1
  fi

  sleep "${INTERVAL}"
  echo
done
