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

Then open http://127.0.0.1:8000/mission-control/v2 and sign in.

## Where things live (`~/.ai-software-factory`)

| Path | What |
|---|---|
| `data/platform.db`, `data/customers.db` | the service's own databases (never the repo's `app.db`) |
| `client-workspaces/` | clients' code, Health Check reports, AI-team copies |
| `logs/` | `mission-control.log`, `mission-control.err.log`, `backup.log` |
| `backups/` | nightly backups at 02:30 (a missed run happens after the Mac wakes) |
| `mission-control.env`, `ai-keys.env` | login and keys, mode 600, **never backed up** |
| `vault.key` | encrypts keys saved in Settings; made on the first save, mode 600, **never backed up** |

Settings (environment variables, set before `install`):
- `ASF_BACKUP_DIR`: put backups elsewhere, e.g. an external disk or an iCloud Drive folder;
- `ASF_BACKUP_KEEP`: how many backups to keep (default 14).

## Saving keys in Settings

Settings → Credentials → Add/Replace saves a key encrypted in `data/platform.db` (AES-256-GCM; the
data key is wrapped with `vault.key`). A key saved there wins over the same key in `ai-keys.env`,
so once all keys are saved you can empty `ai-keys.env`. Backups hold only the encrypted values:
**keep a copy of `vault.key` in your password manager**, or re-enter the keys after restoring
on another Mac. (On Cloud Run, Cloud KMS is used instead, as before.)

## Everyday commands

```bash
~/venv/bin/python -m app.platform.ops status
```

Other commands: `restart` (after pulling new code), `backup` (now), `backups` (list and verify),
`uninstall` (stop; data and backups stay), `restore <backup folder>` (after `uninstall`; the current
data is moved to `before-restore-<time>/`, never deleted).

## Docker (client code runs there)

Client jobs run the client's code only inside Docker containers, so keep Docker Desktop running
(Settings → General → "Start Docker Desktop when you sign in"). `status` shows whether the service
can reach it. The service adds `/usr/local/bin` and `/opt/homebrew/bin` to its PATH, since launchd
starts it without them. If Docker isn't running when a job starts building, the service opens
Docker Desktop in the background and waits up to two minutes for it. Only if it still doesn't
answer does the job pause, with "Start Docker Desktop, then resume", instead of failing.

## What a backup holds

Consistent copies of both databases (SQLite backup API, safe while the service runs), and a tar of
`client-workspaces/` without installed packages, caches or secret files (`.env`, keys, credentials).
A `manifest.json` lists every file's SHA-256; `backups` re-checks them and runs SQLite's
integrity check. Keys and logins are not in backups: keep a copy of them in your password manager.

## After a restart

Missions that were mid-run (planning, building, reviewing) start again by themselves; missions
waiting for you (decisions, OK to run code, paused) stay waiting. Only the service does this
(`ORCA_AUTO_RESUME=1`); a dev server never starts AI work on its own.
