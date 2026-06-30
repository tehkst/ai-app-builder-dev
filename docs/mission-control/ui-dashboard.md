# Mission Control Web Dashboard

This dashboard is the first visual operating console for AI Software Factory.

## Routes

- `/ui`
- `/mission-control/ui`

## Initial panels

- Executive Office
- Company health cards
- Departments
- AI Workforce
- Knowledge Vault

## Approach

The first UI is server-rendered from FastAPI to keep the production slice simple, fast, and low-risk. Later PRs can introduce a richer frontend framework once the operating model is stable.
