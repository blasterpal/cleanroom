#!/bin/sh
# Seed ~/.config/opencode (bind-mounted from data/opencode) with the image's
# baked-in OpenCode config, skills and plugins — without overwriting anything
# already there, so in-container settings persist across rebuilds.
set -eu
seed=/opt/cleanroom/seed/opencode
cfg="${HOME}/.config/opencode"
if [ -d "$seed" ]; then
  mkdir -p "$cfg"
  cp -an "$seed/." "$cfg/" 2>/dev/null || true
fi
exec "$@"
