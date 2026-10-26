# Mission Control as an always-on Mac service

For the supervised pilot, Mission Control runs on the founder's Mac as a background service:
it starts at login, restarts after a crash, keeps the Mac awake while it runs, and backs itself up
every night. It listens on `127.0.0.1` only (not reachable from the network).

## One-time setup

Run these in Terminal from the repo folder (`~/ai-app-builder-dev`):

```bash
~/venv/bin/python -m app.platform.ops setup
```

You type the founder email and a password (12+ characters, not shown). A session secret is generated
for you. Everything goes to `~/.ai-software-factory/mission-control.env`, readable only by you.

```bash
~/venv/bin/python -m app.platform.ops install
```

Then open http://127.0.0.1:8000/mission-control.

## Where things live (`~/.ai-software-factory`)

| Path | What |
|---|---|
| `data/platform.db`, `data/customers.db` | the service's own databases (never the repo's `app.db`) |
| `client-workspaces/` | clients' code, Health Check reports, AI-team copies |
| `logs/` | `mission-control.log`, `mission-control.err.log`, `backup.log` |
| `backups/` | nightly backups at 02:30 (a missed run happens after the Mac wakes) |
| `mission-control.env`, `ai-keys.env` | login and keys, mode 600, **never backed up** |

Settings (environment variables, set before `install`):
- `ASF_BACKUP_DIR`: put backups elsewhere, e.g. an external disk or an iCloud Drive folder;
- `ASF_BACKUP_KEEP`: how many backups to keep (default 14).

## Everyday commands

```bash
~/venv/bin/python -m app.platform.ops status
```

Other commands: `restart` (after pulling new code), `backup` (now), `backups` (list and verify),
`uninstall` (stop; data and backups stay), `restore <backup folder>` (after `uninstall`; the current
data is moved to `before-restore-<time>/`, never deleted).

## What a backup holds

Consistent copies of both databases (SQLite backup API, safe while the service runs), and a tar of
`client-workspaces/` without installed packages, caches or secret files (`.env`, keys, credentials).
A `manifest.json` lists every file's SHA-256; `backups` re-checks them and runs SQLite's
integrity check. Keys and logins are not in backups: keep a copy of them in your password manager.

## After a restart

Missions that were mid-run (planning, building, reviewing) start again by themselves; missions
waiting for you (decisions, OK to run code, paused) stay waiting. Only the service does this
(`ORCA_AUTO_RESUME=1`); a dev server never starts AI work on its own.
