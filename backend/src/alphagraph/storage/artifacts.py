from __future__ import annotations

import json
from pathlib import Path

from alphagraph.schemas import AttemptRecord, RunSnapshot


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def attempt_dir(self, run_id: str, attempt_number: int) -> Path:
        path = self.root / run_id / f"attempt-{attempt_number}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_generated_code(
        self,
        run_id: str,
        attempt_number: int,
        filename: str,
        content: str,
    ) -> Path:
        path = self.attempt_dir(run_id, attempt_number) / filename
        path.write_text(content)
        return path

    def write_execution_result(
        self,
        run_id: str,
        attempt_number: int,
        payload: dict,
    ) -> Path:
        path = self.attempt_dir(run_id, attempt_number) / "execution_result.json"
        path.write_text(json.dumps(payload, indent=2))
        return path

    def write_attempt_snapshot(
        self,
        run_id: str,
        attempt_number: int,
        attempt: AttemptRecord,
    ) -> Path:
        path = self.attempt_dir(run_id, attempt_number) / "attempt_snapshot.json"
        path.write_text(attempt.model_dump_json(indent=2))
        return path

    def write_final_report(self, snapshot: RunSnapshot) -> Path:
        path = self.root / snapshot.run_id / "final_report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot.model_dump_json(indent=2))
        return path
