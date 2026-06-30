# Company Brain Repository

The Company Brain Repository is the persistence boundary for AI Software Factory's institutional memory.

## Purpose

Mission Control should not depend directly on hard-coded company data. It should read company artifacts through a repository abstraction.

## Initial storage

The first implementation uses repository-backed Markdown files under `company/`.

## Future storage

The same interface can later be backed by:

- Cloud SQL
- Knowledge graph storage
- Object storage
- Hybrid repository plus database storage

## Principle

APIs and UI should depend on the Company Brain Repository interface, not on a specific storage implementation.

## Migration path

1. Repository filesystem
2. Repository interface
3. Mission Control API exposure
4. Cloud SQL persistence
5. Knowledge Vault retrieval
6. Company Graph
