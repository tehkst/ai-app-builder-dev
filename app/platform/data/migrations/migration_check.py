from __future__ import annotations

from app.platform.data.migrations.registry import list_migrations, migration_ids


def main() -> None:
    migrations = list_migrations()
    ids = migration_ids()
    assert migrations, "migration registry must not be empty"
    assert len(ids) == len(set(ids)), ids
    assert ids[0] == "0001_base", ids
    assert all(migration.safe_to_repeat for migration in migrations), migrations
    print("MIGRATION CHECK PASSED")


if __name__ == "__main__":
    main()
