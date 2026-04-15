from __future__ import annotations

import sqlite3
from pathlib import Path

from alphagraph.schemas import RunSnapshot


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            create table if not exists runs (
                run_id text primary key,
                status text not null,
                approval_status text not null,
                attempt integer not null,
                snapshot_json text not null
            )
            """
        )
        self.conn.commit()

    def save_snapshot(self, snapshot: RunSnapshot) -> None:
        self.conn.execute(
            """
            insert into runs (run_id, status, approval_status, attempt, snapshot_json)
            values (?, ?, ?, ?, ?)
            on conflict(run_id) do update set
                status = excluded.status,
                approval_status = excluded.approval_status,
                attempt = excluded.attempt,
                snapshot_json = excluded.snapshot_json
            """,
            (
                snapshot.run_id,
                snapshot.status,
                snapshot.approval_status,
                snapshot.attempt,
                snapshot.model_dump_json(),
            ),
        )
        self.conn.commit()

    def get_snapshot(self, run_id: str) -> RunSnapshot | None:
        row = self.conn.execute(
            "select snapshot_json from runs where run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return RunSnapshot.model_validate_json(row[0])
