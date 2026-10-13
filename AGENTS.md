# Cleanroom development environment

**Status:** active — containerized harness at `~/code/cleanroom`
**Tickets:** none
**Reviews:** none

This repository provides an isolated container with OpenCode, Git, Herdr, tmux,
Ruby, Python, PostgreSQL and Rails for harness experimentation and development —
building a fresh application from a standalone specification.

## Location and Git

The project lives at `~/code/cleanroom`, a normal Git repository **outside** any
synced folder. Git is allowed here. Never move it into a Dropbox-synced path —
Dropbox corrupts `.git`.

Parallel work uses git worktrees via the `wt` command:

```sh
wt switch <branch>   # create/switch to a worktree
wt list              # list worktrees
wt remove <branch>   # remove worktree
```

The container mounts `./app` from the current checkout, so run `docker compose`
from the worktree you want the agent to work in. Generate Rails apps inside the
container with `rails new . --database=postgresql`.

## Scope

Maintain the Docker environment here. Application implementation belongs in
`app/`, which appears as `/workspace` inside the container. The builder receives
only `spec/` (mounted read-only as `/spec`) and its new workspace. Do not copy
original application source, host profiles, prior conversations, or the
spec-writing prompt into the builder. Preserve the separation between
specification author and builder.

## Local-only drop folders

`data/` and `blind_data/` are symlinks to directories outside the repository and
are gitignored. They mount writable at `/data` and `/blind_data`. Their contents
must never be committed, and the symlinks themselves must not be committed
either. Docker follows the symlinks when bind-mounting.

## Credentials

Supply OpenAI and Anthropic keys in `.env` (gitignored). `scripts/up` injects the
OpenRouter key from 1Password. Docker Compose injects keys at runtime; the file
is not mounted into `/workspace` or copied into the image. Never print keys or
run commands that dump the full environment or resolved Compose config. Runtime
agents can use their own supplied keys; this container is not a secret boundary
from those agents.

## Browser testing

The container may connect to a browser running on the host over CDP. See
`app/AGENTS.md` for the connection and helper commands. Browsing/test actions
are authorized; sending messages, publishing, purchases, or destructive actions
require explicit authorization. Keep unrelated browser tabs intact.

## Validation

Build the image and run `scripts/check`. Check actual skill discovery,
PostgreSQL access, non-root identity and the CDP connection. No paid model calls
are necessary for environment verification. Docker volumes hold database and
agent state; never put them in a synced folder.
