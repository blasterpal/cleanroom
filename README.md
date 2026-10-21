# Cleanroom

A Docker environment for experimenting with AI agent harnesses using selected
inputs, persistent tooling, and a separate application workspace.

## What it's for

An agent running on your everyday machine can pick up context, configuration,
and files unrelated to the experiment. Cleanroom gives the agent a separate
Linux environment and lets you choose the workspace, specifications, and data
it receives, without mounting your home directory or existing project trees.

Use it to try models, agent settings, skills, and development workflows without
changing your host setup. One use case is building a fresh application from a
standalone specification, without supplying the original implementation or the
specification author's research. Keep those materials out of the mounted inputs.

The current setup includes OpenCode, Herdr, tmux, Git, Ruby/Rails, Python, the
PostgreSQL client, a vendored Matt Pocock skill snapshot, and a browser-testing
helper. The PostgreSQL server is temporarily disabled.
It is a development environment, not an agent framework or hosted service.

## Isolation limits

Cleanroom controls which host directories are mounted; **it is not a hardened
sandbox for untrusted agents or code**, and the name does not imply a formal
legal clean-room process.

- The agent can read and write the mounted workspace and both drop folders.
- Provider keys are supplied at runtime and are accessible to the agent.
- Outbound network access is not restricted by this setup.
- Optional CDP access connects to a host browser, including its authenticated
  websites. Use a dedicated browser profile if that access is inappropriate.
- OpenCode config and skills are shared and must contain no secrets. The provider
  config references `OPENROUTER_API_KEY` through `{env:OPENROUTER_API_KEY}`.
- Every CLI launch requires `cleanroom --name NAME`. Each container mounts only
  that name's auth, session state, and cache volumes. Reusing a name resumes its
  saved state. Compose retains its existing state volumes separately. Stopping
  a container does not clear saved state.

Neither the Docker socket nor the host home directory/browser profile is
mounted. Only supply material and credentials you intend the agent to access.

## Layout

| Path | Purpose |
|---|---|
| `app/` | Application workspace, mounted writable at `/workspace` |
| `spec/` | Input specification, mounted read-only at `/spec` (place the agreed spec at `spec/spec.md`) |
| `data/` | Shared drop folder, mounted writable at `/data`; **outside Git** (see below) |
| `blind_data/` | Second drop folder, mounted writable at `/blind_data`; **outside Git** |
| `setup.sh` | Installs the host `cleanroom` command and builds its image |
| `bin/` | Host-side `cleanroom` CLI |
| `scripts/` | `up`, `dev`, `bash`, `check`, `browser-check`, `install-skills`, `entrypoint.sh` |
| `browser/` | CDP helper (`cdp.mjs`) |
| `config/` | The container's global OpenCode config |
| `vendor/` | Vendored skill snapshot (with upstream license) |

## Local-only drop folders

`data/` and `blind_data/` are local symlinks to directories outside the repository.
Both paths are gitignored; do not force-add their contents or commit the
symlinks. Docker follows the symlink for bind mounts, so `./data:/data` works
unchanged. Both folders are visible to the same agent: `blind_data` is a name,
not a visibility restriction or a hidden evaluation set.

`data/opencode/` stores the container's OpenCode configuration, skills, and
plugins. The entrypoint seeds it from the image without overwriting existing
files. Those settings persist outside the checkout.

Recreate them wherever you keep local-only material:

```sh
mkdir -p "$HOME/cleanroom-local/data" "$HOME/cleanroom-local/blind_data"
ln -s "$HOME/cleanroom-local/data" data
ln -s "$HOME/cleanroom-local/blind_data" blind_data
```

Run these commands from a fresh checkout. If either path already exists,
inspect it before replacing it.

## Getting started

The current host workflow targets macOS with Docker Desktop and Docker Compose.
Keep the checkout outside Dropbox or other synced folders. The helper scripts
use a macOS file timestamp command when checking the credential cache.

### Bash in any workspace

With Docker Desktop running, run setup once from this checkout:

```sh
./setup.sh
cd /path/to/workspace
cleanroom --name my_project
```

`setup.sh` installs the command in `~/.local/bin` and builds the image. If that
directory is not on `PATH`, add it before running `cleanroom`. If `.env` is
missing, setup creates it from `.env.example` with owner-only permissions and
does not overwrite an existing file. The example keys are blank; add the
credentials you want to use. The CLI opens Bash with the current directory
mounted read/write at `/workspace`; type `opencode` inside the container to
start OpenCode. Run `cleanroom build` after changing the image, OpenCode config,
or vendored skills.

The only credential required for OpenRouter is a valid `OPENROUTER_API_KEY`.
Export it in your shell, or put it in `.env` in the **current working directory**.
A nonempty shell value takes precedence. The CLI no longer falls back to the
Cleanroom checkout's `.env` when you run it from another directory.

```sh
cd /path/to/workspace
# Set OPENROUTER_API_KEY in this directory's .env, then:
cleanroom --name a
# Inside the container:
opencode
```

The key is supplied as a runtime environment variable. Before OpenCode starts,
the entrypoint merges it into `~/.local/share/opencode/auth.json` (mode 0600),
preserving other providers. No `/connect` is needed. An unset or empty key leaves
existing auth untouched. The env file is read host-side and never mounted as a
credential file; files covered by the workspace mount are hidden with an empty,
read-only file inside the container. Keep credential files out of Git.

`cleanroom --name a` and `cleanroom --name b` use separate Docker volumes for
OpenCode data (including auth and sessions), state, and caches. The same normalized name
reuses those volumes across workspaces. Config, plugins, and the complete pinned
Matt Pocock skill pack remain shared in `cleanroom-cli-opencode-config`; keep
secrets out of that volume. Gems and Herdr config also remain shared.

`--name` is required for every launch; `build`, `install`, and `--help` do not
require it. Spaces and dashes become underscores. Other special characters are
removed; letters, digits, and underscores are preserved, including letter case.
Quote names containing spaces: `cleanroom --name "Login fix-v2!"` uses
`Login_fix_v2`. Names that become empty are rejected. Names that normalize to the
same value reuse the same state. Existing `cleanroom-cli-seat-<name>-...` volumes
are reused when `<name>` matches the normalized name; no volumes are moved or
deleted.

For an explicit env file, use `cleanroom --name a --env-file /path/to/credentials.env`
or set `CLEANROOM_ENV_FILE`. These select runtime variables and do not change
the shared config or skills. The current workspace is the only host directory
mounted by the CLI. Run `cleanroom build` after changing the image, OpenCode
config, or vendored skills.

### With 1Password

Install the `op` CLI and enable the desktop app's CLI integration (Settings →
Developer → "Integrate with 1Password CLI"). Set your own secret reference:

```sh
export OPENROUTER_OP_REF='op://Vault/Item/field'
docker compose build
./scripts/up      # injects OPENROUTER_API_KEY from 1Password and starts the stack
./scripts/install-skills  # refreshes the OpenCode skill pack from upstream
./scripts/dev     # OpenCode TUI in the dev container
```

`scripts/up` reads the OpenRouter key from 1Password using the `op://` reference
in `OPENROUTER_OP_REF` (for example `op://Vault/Item/field`), exports it as
`OPENROUTER_API_KEY`, and runs `docker compose up -d`. It does not write the key
to `.env`; it creates a mode 0600 template if needed. It requires the
1Password desktop app's CLI integration (Settings → Developer → "Integrate with
1Password CLI"). The key is cached for one hour (`OPENROUTER_KEY_CACHE`,
`OPENROUTER_KEY_CACHE_TTL`). Fill `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` by hand
to use those providers.

The startup auth entry and the container's global
`~/.config/opencode/opencode.json` (from `config/opencode.json`) both use the
injected `OPENROUTER_API_KEY`. No interactive login is needed. Choose a model
with OpenCode's `/models`; none is hardcoded.

### Without 1Password

```sh
cp .env.example .env
chmod 600 .env
# Edit .env locally to set OPENROUTER_API_KEY. Do not commit it.
docker compose build
docker compose up -d
./scripts/install-skills
./scripts/dev
```

The supplied provider config wires OpenRouter to its environment key. Other
providers need their own OpenCode connection/configuration as well as credentials.

Further scripts: `./scripts/dev bash` (dev shell), `./scripts/dev herdr`
(container-local terminal), `./scripts/check` (offline environment checks),
`./scripts/browser-check` (loads a container page in the host browser, then
closes its QA tab).

`./scripts/install-skills` installs the latest `mattpocock/skills` pack for
OpenCode into the persistent global skill directory. It uses copy mode so the
skills remain inside Cleanroom's mounted OpenCode config, and does not add files
to the mounted `app/` workspace. The image's pinned vendored skills remain the
offline baseline; this script is an explicit, network-dependent refresh.

## Specification-driven builds and database

The default instructions in `app/AGENTS.md` describe a Rails/PostgreSQL builder
that waits for `/spec/spec.md`. Supply that document for a specification-driven
build, or adapt those instructions for a different harness experiment.

The Rails app lives in `app/` (`/workspace`); scaffold with
`rails new . --database=postgresql`. Bind the server to `0.0.0.0:3000`; it is
published at `http://127.0.0.1:13000` (`RAILS_HOST_PORT` in `.env`). The local
PostgreSQL server is temporarily removed from Compose, so no local database URLs
are configured and database-dependent app/test runs need an explicitly supplied
external database or restoration of the Compose service. The existing Postgres
Docker volume is left untouched but is not mounted. Gems persist in a Docker
volume.

## Browser testing

If a host browser is running with CDP, set `BRAVE_CDP_URL` (default
`http://host.docker.internal:9222`). The container attaches to it for website
testing; the helper handles loopback WebSocket rewriting and the Host-header
restriction. This deliberately extends the environment beyond its mounted
files, so keep QA tabs separate and close only the ones you open. Do not restart
the host browser or expose its CDP port.

```sh
./scripts/dev node /opt/browser/cdp.mjs status
```

## Persistence and stopping

Sessions, caches, gems and Herdr state persist in Docker named volumes outside
any synced folder. The existing Postgres data volume is also retained, but the
current Compose configuration does not mount it. `docker compose down` stops the
stack and keeps its volumes; `docker compose down -v` deletes the volumes declared
in the current Compose configuration. No Docker socket, host home directory, or
browser profile is mounted.

## Before publishing your own checkout

Review the staged files and Git history, not just the current directory. Ignore
rules do not remove previously committed files. Keep inputs, transcripts,
credentials, and private specifications out of commits; review new files under
`app/` and `spec/` before adding them. Never publish runtime Docker volumes or
images that contain private inputs or stored credentials.

## License

The harness is MIT licensed — see [`LICENSE`](LICENSE). The vendored skills
retain their upstream [MIT license](vendor/MATT-POCOCK-LICENSE); their source and
pinned commit are recorded in [`vendor/skills.lock.json`](vendor/skills.lock.json).
