from __future__ import annotations

from app.platform.auth.journal import Journal, JournalRecord


def main() -> None:
    journal = Journal()
    first = JournalRecord(
        record_id="record1",
        tenant_id="tenant1",
        subject_id="user1",
        action="login",
        target="session",
        outcome="success",
        metadata={"request_id": "request1"},
    )
    journal.append(first)
    assert journal.list_all() == [first]
    assert journal.list_for_tenant("tenant1") == [first]
    assert journal.list_for_tenant("tenant2") == []

    try:
        journal.append(first)
    except ValueError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    assert duplicate_rejected is True

    print("D5.4 JOURNAL CHECK PASSED")


if __name__ == "__main__":
    main()
