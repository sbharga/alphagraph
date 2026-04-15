from pathlib import Path

from fastapi.testclient import TestClient

from alphagraph.app import create_app


def test_api_starts_run_returns_snapshot_and_allows_approval(tmp_path: Path) -> None:
    app = create_app(
        base_dir=tmp_path,
        dataset_path=Path(__file__).resolve().parents[1] / "data" / "prices.csv",
        run_mode="inline",
    )
    client = TestClient(app)

    created = client.post("/runs", json={})
    assert created.status_code == 201

    payload = created.json()
    assert payload["status"] == "awaiting_approval"
    assert payload["approval_status"] == "pending"
    assert payload["phase"] == "awaiting_approval"
    assert payload["supervisor_decision"] == "run_human_review"
    assert payload["current_node"] == "human_in_the_loop"
    assert len(payload["attempts"]) == 2

    run_id = payload["run_id"]

    fetched = client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run_id

    approved = client.post(f"/runs/{run_id}/approve", json={"approved": True})
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["phase"] == "finalized"

    report_name = Path(approved.json()["final_report_path"]).name
    artifact = client.get(f"/runs/{run_id}/artifacts/{report_name}")
    assert artifact.status_code == 200
    assert "run_id" in artifact.text
