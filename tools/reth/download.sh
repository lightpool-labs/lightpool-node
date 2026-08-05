#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${ROOT}/bin"
DOWNLOAD_DIR="${ROOT}/downloads"
VERSION="${RETH_VERSION:-v2.4.1}"

mkdir -p "${BIN_DIR}" "${DOWNLOAD_DIR}"

OS="$(uname -s)"
ARCH="$(uname -m)"

case "${OS}-${ARCH}" in
  Linux-x86_64)
    TARGET="x86_64-unknown-linux-gnu"
    ;;
  Linux-aarch64|Linux-arm64)
    TARGET="aarch64-unknown-linux-gnu"
    ;;
  Darwin-arm64|Darwin-aarch64)
    TARGET="aarch64-apple-darwin"
    ;;
  *)
    echo "Unsupported platform: ${OS}-${ARCH}" >&2
    exit 1
    ;;
esac

ASSET="reth-${VERSION}-${TARGET}.tar.gz"
URL="https://github.com/paradigmxyz/reth/releases/download/${VERSION}/${ASSET}"
ARCHIVE="${DOWNLOAD_DIR}/${ASSET}"

if [[ -x "${BIN_DIR}/reth" ]]; then
  echo "reth already present at ${BIN_DIR}/reth"
  "${BIN_DIR}/reth" --version || true
  exit 0
fi

echo "Downloading ${URL}"
curl -fL --retry 3 -o "${ARCHIVE}" "${URL}"
tar -xzf "${ARCHIVE}" -C "${BIN_DIR}"
chmod +x "${BIN_DIR}/reth"

echo "Installed:"
"${BIN_DIR}/reth" --version
echo "Binary: ${BIN_DIR}/reth"
