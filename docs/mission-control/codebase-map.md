# Codebase Map

An interactive, plain-language map of a client's codebase: the main parts of the app, the outside
services it uses, how they connect, and a plain name and description for every file and endpoint.
It's for understanding a codebase you've taken over, for explaining it to the client, and as a
deliverable you can send them. The design follows [Floorplan](https://github.com/haydenschmitty/floorplan)
(MIT; see `app/platform/codebase_map/LICENSE-floorplan.txt`), rebuilt in Python on this platform's
own scanners, AI providers, consent gate and redaction.

## Using it

Mission Control → Clients → a client → a codebase → **Codebase Map**.

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
