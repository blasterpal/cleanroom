# Application builder

Build the application from the standalone specification at `/spec/spec.md`.
Mandatory technologies: Ruby on Rails and PostgreSQL. Make implementation
choices from that specification. If it is missing, ask for it before
implementing product behavior; the spec-writing prompt is not the final
specification.

## Workspace and tools

The working directory is `/workspace`, mounted from the `app/` directory of the
cleanroom repository (outside any synced folder on the host). Git is allowed in
this workspace: scaffold with `rails new . --database=postgresql`; preserve this
file and `opencode.json`. Worktrees and branches are managed from the host with
the `wt` command; ask before switching the mounted worktree.

Ruby, Rails, Node/npm, Git, tmux, Python 3, PostgreSQL client, OpenCode, Herdr,
and the vendored skills are installed. Skills are in `~/.config/opencode/skills/`;
use OpenCode's skill tool to discover/load them. Skills that mention Git
workflows or Claude-only hooks remain subject to these workspace rules. Herdr is
container-local, separate from any host Herdr session. Start `herdr` from an
interactive shell, then start OpenCode in its pane; `herdr --skill` describes its
controls.

`DATABASE_URL` points to the local development PostgreSQL service.
`TEST_DATABASE_URL` points to `app_test`; configure the Rails test environment to
use it rather than accidentally reusing the development URL. Bind the Rails
server to `0.0.0.0:3000` for host access at `http://127.0.0.1:13000` (or the
configured host port). `/data` and `/blind_data` are shared drop folders (the `data/` and `blind_data/`
symlinks in the repo) for files supplied for evals and testing; treat them as
provided input, not part of the app source.

## Host browser

Use the already-running host browser through CDP for interactive website
testing. Do not launch a replacement browser, read the host browser profile, or
close unrelated tabs.

The endpoint is supplied by `BRAVE_CDP_URL` (default
`http://host.docker.internal:9222`). Use the installed helper:

- `node /opt/browser/cdp.mjs status` — verify attachment without listing unrelated page content.
- `node /opt/browser/cdp.mjs open http://127.0.0.1:13000` — create a dedicated QA tab and return its stable target ID.
- `node /opt/browser/cdp.mjs inspect TARGET_ID` — inspect visible text in that tab.
- `node /opt/browser/cdp.mjs screenshot TARGET_ID /workspace/tmp/qa.png` — capture that tab.
- `node /opt/browser/cdp.mjs eval TARGET_ID 'document.title'` — evaluate JavaScript in that tab for assertions/interactions.
- `node /opt/browser/cdp.mjs close TARGET_ID` — close only the dedicated QA tab you created.

URLs containing `127.0.0.1`/`localhost` refer to the host when loaded by that
browser; the container's Rails server must have its port published by
`scripts/dev`. The helper rewrites the CDP WebSocket endpoint to the reachable
host address. If connection fails, report it; do not change the host browser's
launch flags or expose its CDP port publicly.

Browse and exercise the new application's UI as needed. Keep test data separate
from live external systems. Ask before consequential external actions such as
sending messages, publishing, deleting live data, or purchases. Browser access
includes authenticated websites, so it deliberately extends this environment's
access beyond the mounted source files.

## Keys and completion

Provider keys are injected at runtime. Never print or persist them in source,
logs, screenshots or reports. Do not inspect unrelated host files. Provide
runnable code, meaningful tests, and concise implementation/validation notes. Do
not claim a model or browser test ran unless it actually ran.
