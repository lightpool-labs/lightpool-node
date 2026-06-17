#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${ROOT}/bin"
DEST="${BIN_DIR}/lightpool"

ARCHIVE=""
if compgen -G "${BIN_DIR}/lightpool-v*.tar.gz" > /dev/null; then
  ARCHIVE="$(ls -t "${BIN_DIR}"/lightpool-v*.tar.gz | head -1)"
fi

if [[ -z "${ARCHIVE}" ]]; then
  echo "extract-binary: no lightpool-v*.tar.gz found in ${BIN_DIR}" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

tar -xzf "${ARCHIVE}" -C "${TMP}"

EXTRACTED=""
while IFS= read -r path; do
  EXTRACTED="${path}"
  break
done < <(find "${TMP}" -type f -name lightpool ! -path '*/.*')

if [[ -z "${EXTRACTED}" ]]; then
  echo "extract-binary: lightpool binary not found inside ${ARCHIVE}" >&2
  exit 1
fi

cp "${EXTRACTED}" "${DEST}"
chmod +x "${DEST}"
echo "extract-binary: ${ARCHIVE} -> ${DEST}"
