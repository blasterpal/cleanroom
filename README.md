# Cleanroom — isolated agent harness

A disposable, containerized Linux environment for building a fresh application
from a **standalone specification**. Only the selected workspace, specification,
and drop folders are bind-mounted; host-browser access is available through CDP.
Keep original source and author context out of the supplied inputs.

Installed: OpenCode, Git, Herdr, tmux, Ruby/Rails, Python, PostgreSQL, a
vendored skill snapshot, and a CDP helper for host-browser access.

## Layout

| Path | Purpose |
|---|---|
| `app/` | Application workspace, mounted writable at `/workspace` |
| `spec/` | Input specification, mounted read-only at `/spec` (place the agreed spec at `spec/spec.md`) |
| `data/` | Shared drop folder, mounted writable at `/data`; **outside Git** (see below) |
| `blind_data/` | Second drop folder, mounted writable at `/blind_data`; **outside Git** |
| `scripts/` | `up`, `dev`, `bash`, `check`, `browser-check`, `entrypoint.sh` |
| `browser/` | CDP helper (`cdp.mjs`) |
| `config/` | The container's global OpenCode config |
| `vendor/` | Vendored skill snapshot (with upstream license) |

## Local-only drop folders

`data/` and `blind_data/` are **symlinks to directories outside the repository**,
so their contents never enter Git. They are ignored via `/data` and
`/blind_data` in `.gitignore`; do not replace them with tracked directories or
commit the symlinks. Docker follows the symlink for bind mounts, so
`./data:/data` works unchanged.

Recreate them wherever you keep local-only material:

```sh
mkdir -p "$HOME/cleanroom-local/data" "$HOME/cleanroom-local/blind_data"
ln -sfn "$HOME/cleanroom-local/data" data
ln -sfn "$HOME/cleanroom-local/blind_data" blind_data
```

## Start

```sh
docker compose build
./scripts/up      # injects OPENROUTER_API_KEY from 1Password and starts the stack
./scripts/dev     # OpenCode TUI in the dev container
```

`scripts/up` reads the OpenRouter key from 1Password using the `op://` reference
in `OPENROUTER_OP_REF` (for example `op://Vault/Item/field`), writes it into the
gitignored `.env` (mode 0600), and runs `docker compose up -d`. It requires the
1Password desktop app's CLI integration (Settings → Developer → "Integrate with
1Password CLI"). The key is cached for one hour (`OPENROUTER_KEY_CACHE`,
`OPENROUTER_KEY_CACHE_TTL`). Fill `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` by hand
to use those providers.

Keys reach OpenCode through the container's global
`~/.config/opencode/opencode.json` (from `config/opencode.json`), which reads
`OPENROUTER_API_KEY` from the injected environment — no interactive login
needed. Choose a model with OpenCode's `/models`; none is hardcoded.

Further scripts: `./scripts/dev bash` (dev shell), `./scripts/dev herdr`
(container-local terminal), `./scripts/check` (offline environment checks),
`./scripts/browser-check` (loads a container page in the host browser, then
closes its QA tab).

## Application and database

The Rails app lives in `app/` (`/workspace`); scaffold with
`rails new . --database=postgresql`. Bind the server to `0.0.0.0:3000`; it is
published at `http://127.0.0.1:13000` (`RAILS_HOST_PORT` in `.env`). PostgreSQL
is reachable only on the Compose network, holds `app_development` and
`app_test`, and has development-only credentials. Point tests at
`TEST_DATABASE_URL`; the default `DATABASE_URL` targets development. Gems
persist in a Docker volume.

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

Sessions, caches, gems, Herdr state and database files persist in Docker named
volumes outside any synced folder. `docker compose down` stops the stack and
keeps the volumes; `docker compose down -v` deletes them. No Docker socket, host
home directory, or browser profile is mounted.

## License

MIT — see [`LICENSE`](LICENSE).
