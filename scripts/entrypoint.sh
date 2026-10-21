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
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  # Read the key from the environment so it never appears in process arguments.
  python3 - <<'PYTHON'
import json
import os
from pathlib import Path
import tempfile

path = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "opencode/auth.json"
path.parent.mkdir(parents=True, exist_ok=True)
try:
    auth = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(auth, dict):
        raise ValueError()
except (ValueError, OSError):
    raise SystemExit("Cannot read OpenCode auth.json; existing credentials were left untouched.") from None
auth["openrouter"] = {"type": "api", "key": os.environ["OPENROUTER_API_KEY"]}
fd, temporary = tempfile.mkstemp(prefix=".auth-", dir=path.parent)
try:
    with os.fdopen(fd, "w") as stream:
        json.dump(auth, stream)
        stream.write("\n")
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PYTHON
fi
exec "$@"
