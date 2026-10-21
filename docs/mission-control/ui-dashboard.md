# Mission Control Web Dashboard

This dashboard is the first visual operating console for AI Software Factory.

## Routes

- `/ui`
- `/mission-control/ui` (Mission Control, redesign: `app/platform/ui/mc2/`)
- `/mission-control/insights/{organisation,memory,architecture,lineage}` (Insights pages; the previous
  dashboard at `/mission-control/classic` was retired on 2026-10-21)

## Initial panels

- Executive Office
- Company health cards
- Departments
- AI Workforce
- Knowledge Vault

## Approach

The first UI is server-rendered from FastAPI to keep the production slice simple, fast, and low-risk. Later PRs can introduce a richer frontend framework once the operating model is stable.
