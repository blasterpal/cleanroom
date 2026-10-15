#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -P "$(dirname "$0")" >/dev/null 2>&1 && pwd)

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI not found. Install Docker Desktop, then run setup.sh again." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop, then run setup.sh again." >&2
  exit 1
fi

echo "Installing the cleanroom command..."
"$ROOT/bin/cleanroom" install

echo "Building the Cleanroom image..."
"$ROOT/bin/cleanroom" build

echo "Setup complete. From any workspace directory, run: cleanroom"
