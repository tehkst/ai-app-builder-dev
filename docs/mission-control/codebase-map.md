# Codebase Map

An interactive, plain-language map of a client's codebase: the main parts of the app, the outside
services it uses, how they connect, and a plain name and description for every file and endpoint.
It's for understanding a codebase you've taken over, for explaining it to the client, and as a
deliverable you can send them. The design follows [Floorplan](https://github.com/haydenschmitty/floorplan)
(MIT; see `app/platform/codebase_map/LICENSE-floorplan.txt`), rebuilt in Python on this platform's
own scanners, AI providers, consent gate and redaction.

## Using it

Mission Control → Clients → a client → a codebase → **Codebase Map**.

Or ask Jarvis for one ("create the system map of my app", "codebase map of Kopi Bakery", "draw a
floorplan"). Jarvis answers with buttons instead of a written map: **Open the map** for a finished
map, **Make a map** / **Update the map** for each codebase (those named in the message, otherwise
all of them), and **Map AI Software Factory itself**, which files this platform's own repository
under an internal client the first time. The same confirmation as below appears before any code is
sent; Jarvis then checks every 15 seconds and adds **Open the map** when it's ready
(`app/platform/codebase_map/jarvis.py`).

- **Make a map.** Needs the code fetched (a Health Check isn't required). Like jobs and the Audit,
  this sends a redacted copy of the code to the AI provider in Settings, so you confirm the client
  agreed; the dialog shows that provider's terms. It takes a few minutes.
- **Open the map.** Opens the viewer in a new tab:
  - The overview shows the app's parts and outside services. Double-click a part (or press Enter
    twice) to go inside: its sub-parts and files in the middle, what uses it on the left, and what
    it relies on on the right. More than 24 files of its own are grouped by folder.
  - Click a card for its details: what it does, its endpoints, what it uses and what uses it.
  - Lines: grey = uses (imports), blue = web requests matched to the endpoint that answers them,
    purple dashed = outside services, orange dotted = connections the Cartographer added (webhooks,
    scheduled jobs, queues).
  - **Start here** plays a short tour (also on the first visit). **Flows** walks through the app's
    main jobs step by step. **Search** finds parts, files and endpoints. **Technical** shows paths,
    file names and what each file defines.
  - **Health** lists what the scan can see: passwords or keys written into the code (never their
    values), very long files, and files nothing seems to use. **Show on map** marks them on the cards.
  - **Download for the client** saves the map as one HTML file that opens in any browser, with no
    folder paths from this Mac. Health is left out unless you include it: it says where secrets sit.
- **Update the map** after the code changes: the parts are kept, descriptions carry over to files
  whose content or definitions didn't change (also when moved or renamed), and only new and changed
  files are read again, so updates cost much less. If a lot of new code fits no part, the parts are
  updated too. **Redraw from scratch** starts over.

**Maps** in the left menu lists every codebase with its latest map in one place: Open, Make,
Update and Redraw, with the same confirmation (`app/platform/ui/mc2/maps_script.py`).

## A living record

A map keeps itself current. Each time a client job is delivered (pull request, branch or patch
download), the codebase's map is updated from the delivered code, re-reading only the changed files,
and the job appears as **Recent work**:

- On the map, changed files are tagged **New** or **Changed**, and every part shows how many of its
  files changed. **Recent work** in the header lists each job: what was asked, the handover summary,
  whether it was fully checked, how it was delivered (with the pull request link), who approved it
  and what the AI cost. The last 5 jobs are kept.
- The Maps screen and the Clients card say "Updated automatically after delivering …", and Maps
  lists each codebase's history (what made each version, its AI cost, and a link to open it).
- It only happens for code you've already mapped, and only when the AI provider and its terms are
  still the ones the client agreed to for that job. Otherwise the delivery goes ahead and Mission
  Control tells you to update the map from Maps (with a fresh confirmation).
- The map drawn after a delivery shows the delivered code. An update from Maps redraws from the code
  as received (the client may not have merged yet), and keeps the Recent work for files still there.
- The copy you download for the client includes Recent work without your email or internal ids.

Code: `clients/maps.after_delivery`, `codebase_map/recent.py`; each map row stores what made it
(`trigger_json`, migration `20261113_01_platform_client_map_trigger`).

## How it works

`app/platform/codebase_map/`:

1. `scan.py` + `routes.py` (no AI, nothing run): files and their sizes, what each defines and its
   doc comment, imports (the impact map's), outside packages and hosts, endpoints (Flask, FastAPI,
   Django, Express/Fastify/Koa/Hono with router mounts, Next.js, Laravel, WordPress REST and
   admin-ajax) and web requests (fetch, axios and similar, jQuery, requests/httpx, wp_remote_*,
   curl, Laravel Http), and which request reaches which endpoint.
2. `cartographer.py`: the Codebase Cartographer (`company/workforce/roles/cartographer.md`) reads the
   scan summary and a redacted copy of the code and writes the architecture: parts with path globs,
   outside services with packages/hosts, extra connections, flows and a tour. `build.check_architecture`
   names any problems (unknown parents, steps pointing nowhere, over 10% of files unclaimed) and the
   Cartographer gets one round to fix them. Then it names and describes every file and endpoint from
   per-part worksheets (batches of up to 60 files, small parts sharing a batch, 3 at a time, up to 1,500
   files per map). A real run on the 12-file sample app (DeepSeek v4 Pro, before batching was shared)
   took 4½ minutes and cost $0.15; cost grows with the number of files and parts.
3. `build.py`: every file goes to the deepest part whose globs match; the graph links files by
   imports, matched web requests, packages and hosts; Health is computed.
4. `app/platform/clients/maps.py` stores each map as JSON under the client's folder
   (`~/.ai-software-factory/client-workspaces/<client>/maps/`) with a row in `platform_client_maps`
   (provider, consent, the terms version shown, AI cost). The viewer is
   `app/platform/ui/mc2/map_viewer.py`; everything AI-written is escaped before it reaches the page.

Checked by `app.platform.codebase_map.check` (scripted Cartographer, sample codebase in `sample.py`).

## Not built yet

Compared with Floorplan: asking questions of the map, a Screens view (start from a page and see
everything behind it), "Recent work" highlights after AI jobs, and blueprints (a map planned from a
spec before any code exists).
