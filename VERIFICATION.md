# Environment verification — 2026-10-11

Docker image built successfully on the Mac's Linux ARM64 Docker runtime.

| Check | Result |
|---|---|
| Non-root execution | Passed; development user UID 1000 |
| Ruby | 3.4.11 |
| Rails | 8.1.4 |
| Node | 24.21.0 |
| OpenCode | 1.19.0 |
| Herdr | 0.9.3; OpenCode integration current, v13 |
| Skills | All 38 vendored Matt Pocock skills, Herdr skill, and OpenCode built-in customize-opencode discovered |
| PostgreSQL | Development and test connections passed before database names were generalized; current app_development/app_test configuration has not been retested |
| Brave CDP | Attached to Mac browser, version 154.0.8037.98 |
| End-to-end browser | Container-served page opened in a dedicated Mac Brave tab; title/text/JavaScript assertions passed; screenshot saved; QA tab closed |
| Repository location | Outside any synced folder; Git enabled |

The screenshot is `app/tmp/browser-smoke.png`. No original application code or host tree is mounted. API key placeholders are blank; no paid model calls were made. Rails application generation/boot and real provider authentication have not been tested because no product application or keys have been supplied. PostgreSQL state remains in a Docker volume; the database service was started for verification.

## OpenCode authentication and seats — 2026-10-21

Built `cleanroom:local` and verified startup through the actual CLI with fresh
volumes, leaving existing user volumes intact. Temporary test volumes were
removed afterward.

| Check | Result |
|---|---|
| Host regression suite | All 8 tests passed: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` |
| Shell and Compose syntax | `sh -n` passed for the changed scripts; `docker compose config --quiet` passed |
| Fresh `.env`-only startup | Auth seeded before OpenCode, mode 0600; mounted workspace `.env` unreadable as credentials |
| Live provider call | `openrouter/openai/gpt-4.1-nano` responded successfully without `/connect` |
| Seat isolation | Separate auth files; seat A's real OpenCode session survived restart and was absent in seat B |
| Concurrent starts | Two seats simultaneously seeded distinct shell keys, overriding their working directory's `.env` |
| Existing credentials | Other providers preserved; missing/empty key leaves auth untouched; malformed auth fails without exposing or replacing it |
| 1Password | Cold cache, warm cache, environment injection, unchanged `.env`, and error-output redaction verified with fixtures |
| Secret scans | No OpenRouter key found in tracked files, Git history, image layers/metadata, shared OpenCode config, or test container/OpenCode logs |

The live provider test needed the host's trusted CA certificates supplied to the
test container through `NODE_EXTRA_CA_CERTS` because this network presents a
certificate chain absent from the image's trust store. TLS verification remained
enabled. This test-only certificate setup does not change the image or CLI.

### Required Cleanroom names

The CLI now requires `--name` for launches; `build`, `install`, and `--help`
remain available without a name. All 10 host regression tests pass, including
normalization, empty-name rejection, state reuse, and separate named mounts.
A Docker check confirmed that a name containing spaces and punctuation reopens
saved data through its normalized spelling, while another name cannot see that
data. Shell syntax and whitespace checks passed. The image is unchanged by this
host CLI update.
