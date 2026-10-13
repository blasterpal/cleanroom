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
