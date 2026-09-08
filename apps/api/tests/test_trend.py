from __future__ import annotations

from uuid import UUID, uuid4

from test_workspace import _workspace_client


def _machine_and_site(client, organization_id: UUID) -> tuple[str, str]:
    site = client.get(f"/api/v1/organizations/{organization_id}/sites").json()["items"][0]
    machine = client.get(
        f"/api/v1/organizations/{organization_id}/sites/{site['id']}/machines"
    ).json()["items"][0]
    return site["id"], machine["id"]


def _case(
    client,
    organization_id: UUID,
    site_id: str,
    machine_id: str,
    performed_at: str,
    folder_name: str,
) -> str:
    folder = client.post(
        f"/api/v1/organizations/{organization_id}/folders", json={"name": folder_name}
    )
    assert folder.status_code == 201, folder.text
    response = client.post(
        f"/api/v1/organizations/{organization_id}/qa-cases",
        json={
            "site_id": site_id,
            "machine_id": machine_id,
            "primary_folder_id": folder.json()["id"],
            "qa_type": "Machine QA",
            "qa_cycle": "DAILY",
            "performed_at": performed_at,
            "title": folder_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _measurements(
    output_factor: float,
    energy: str = "6X",
) -> list[dict[str, object]]:
    context = {"energy": energy, "detector": "D1", "phantom": "P1"}
    return [
        {
            "metric_key": "output_factor",
            "value": output_factor,
            "unit": "%",
            "context": context,
        },
        {"metric_key": "symmetry", "value": 1.0, "unit": "%", "context": context},
        {"metric_key": "flatness", "value": 100.0, "unit": "%", "context": context},
    ]


def _completed_run(
    client,
    organization_id: UUID,
    protocol_id: str,
    case_id: str,
    output_factor: float,
    energy: str = "6X",
) -> str:
    response = client.post(
        f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
        json={
            "protocol_version_id": protocol_id,
            "measurements": _measurements(output_factor, energy),
        },
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    evaluated = client.post(f"/api/v1/machine-qa-runs/{run_id}/evaluate")
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["status"] == "COMPLETED"
    return run_id


def _seed_trend_data(client, organization_id: UUID) -> tuple[str, str, str, str]:
    site_id, machine_id = _machine_and_site(client, organization_id)
    protocol = client.post(f"/api/v1/organizations/{organization_id}/machine-qa/protocols/seed")
    assert protocol.status_code == 201, protocol.text
    protocol_id = protocol.json()["id"]
    case_one = _case(
        client,
        organization_id,
        site_id,
        machine_id,
        "2026-09-05T08:00:00Z",
        "Trend day one",
    )
    case_two = _case(
        client,
        organization_id,
        site_id,
        machine_id,
        "2026-09-05T12:00:00Z",
        "Trend day two",
    )
    run_one = _completed_run(client, organization_id, protocol_id, case_one, 100.0)
    run_two = _completed_run(client, organization_id, protocol_id, case_two, 104.0, energy="10X")
    return machine_id, protocol_id, run_one, run_two


def test_trend_query_keeps_incompatible_context_in_separate_series() -> None:
    with _workspace_client() as (client, organization):
        machine_id, _, _, _ = _seed_trend_data(client, organization.id)
        response = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"metric_key": "output_factor", "aggregate": "raw"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total_points"] == 2
        assert len(body["series"]) == 2
        assert {series["context"]["energy"] for series in body["series"]} == {"6X", "10X"}
        assert "TREND_SERIES_INCOMPATIBLE" in " ".join(body["warnings"])
        assert all(series["machine_id"] == machine_id for series in body["series"])


def test_trend_baseline_outlier_aggregation_and_context_filter() -> None:
    with _workspace_client() as (client, organization):
        machine_id, _, _, _ = _seed_trend_data(client, organization.id)
        baseline = client.post(
            f"/api/v1/organizations/{organization.id}/trend/baselines",
            json={
                "machine_id": machine_id,
                "metric_key": "output_factor",
                "unit": "%",
                "name": "6X output baseline",
                "baseline_value": 100.0,
                "tolerance": 2.0,
                "action_level": 3.0,
                "effective_from": "2026-09-01T00:00:00Z",
                "context": {"energy": "6X", "detector": "D1", "phantom": "P1"},
            },
        )
        assert baseline.status_code == 201, baseline.text
        assert baseline.json()["version_number"] == 1

        raw = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={
                "metric_key": "output_factor",
                "energy": "6X",
                "aggregate": "raw",
            },
        )
        assert raw.status_code == 200, raw.text
        point = raw.json()["series"][0]["points"][0]
        assert point["baseline_value"] == 100.0
        assert point["baseline_delta"] == 0.0
        assert point["is_outlier"] is False

        daily = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={
                "metric_key": "output_factor",
                "energy": "6X",
                "aggregate": "day",
                "timezone": "Asia/Ho_Chi_Minh",
            },
        )
        assert daily.status_code == 200, daily.text
        series = daily.json()["series"]
        assert len(series) == 1
        bucket = series[0]["buckets"][0]
        assert bucket["count"] == 1
        assert bucket["mean"] == 100.0
        assert bucket["source_run_ids"]


def test_trend_export_and_source_drilldown_preserve_provenance() -> None:
    with _workspace_client() as (client, organization):
        _, _, run_id, _ = _seed_trend_data(client, organization.id)
        response = client.get(
            f"/api/v1/organizations/{organization.id}/trend/export",
            params={"metric_key": "output_factor", "energy": "6X", "export_format": "CSV"},
        )
        assert response.status_code == 200, response.text
        assert "source_run_id" in response.text
        assert run_id in response.text

        payload = client.get(
            f"/api/v1/organizations/{organization.id}/trend/export",
            params={"metric_key": "output_factor", "energy": "6X", "export_format": "JSON"},
        )
        assert payload.status_code == 200, payload.text
        point_id = payload.json()["series"][0]["points"][0]["id"]
        source = client.get(f"/api/v1/trend-points/{point_id}/source")
        assert source.status_code == 200, source.text
        assert source.json()["machine_qa_run"]["id"] == run_id
        assert source.json()["qa_case"]["qa_cycle"] == "DAILY"


def test_trend_rebuild_is_idempotent() -> None:
    with _workspace_client() as (client, organization):
        _, _, _, _ = _seed_trend_data(client, organization.id)
        first = client.post(f"/api/v1/organizations/{organization.id}/trend/rebuild")
        second = client.post(f"/api/v1/organizations/{organization.id}/trend/rebuild")
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert first.json()["created_points"] == 0
        assert first.json()["existing_points"] == 6
        assert second.json()["created_points"] == 0
        assert second.json()["existing_points"] == 6


def test_trend_maintenance_event_revisions_and_stale_update() -> None:
    with _workspace_client() as (client, organization):
        machine_id, _, _, _ = _seed_trend_data(client, organization.id)
        created = client.post(
            f"/api/v1/organizations/{organization.id}/trend/events",
            json={
                "machine_id": machine_id,
                "event_type": "SERVICE",
                "title": "Planned service",
                "started_at": "2026-09-06T01:00:00Z",
                "ended_at": "2026-09-06T03:00:00Z",
                "notes": "Beam calibration",
                "metadata": {"ticket": "QA-42"},
            },
        )
        assert created.status_code == 201, created.text
        event = created.json()
        assert event["revision_number"] == 1

        updated = client.patch(
            f"/api/v1/trend-events/{event['id']}",
            json={"expected_revision": 1, "title": "Completed service"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["revision_number"] == 2

        stale = client.patch(
            f"/api/v1/trend-events/{event['id']}",
            json={"expected_revision": 1, "title": "Stale edit"},
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["code"] == "MAINTENANCE_REVISION_CONFLICT"

        revisions = client.get(f"/api/v1/trend-events/{event['id']}/revisions")
        assert revisions.status_code == 200, revisions.text
        assert [item["revision_number"] for item in revisions.json()] == [1, 2]

        trend = client.get(f"/api/v1/organizations/{organization.id}/trend")
        assert trend.status_code == 200, trend.text
        assert trend.json()["maintenance_events"][0]["title"] == "Completed service"


def test_trend_invalid_inputs_empty_state_and_organization_scope() -> None:
    with _workspace_client() as (client, organization):
        empty = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"metric_key": "not_yet_recorded"},
        )
        assert empty.status_code == 200, empty.text
        assert empty.json()["total_points"] == 0
        assert any(item.startswith("TREND_EMPTY") for item in empty.json()["warnings"])

        invalid_range = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"from": "2026-09-10T00:00:00Z", "to": "2026-09-01T00:00:00Z"},
        )
        assert invalid_range.status_code == 422, invalid_range.text
        assert invalid_range.json()["code"] == "DATE_RANGE_INVALID"

        end_exclusive = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={
                "metric_key": "output_factor",
                "from": "2026-09-05T08:00:00Z",
                "to": "2026-09-05T08:00:00Z",
            },
        )
        assert end_exclusive.status_code == 200, end_exclusive.text
        assert end_exclusive.json()["total_points"] == 0

        invalid_timezone = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"timezone": "Not/A_Timezone"},
        )
        assert invalid_timezone.status_code == 422, invalid_timezone.text
        assert invalid_timezone.json()["code"] == "TREND_TIMEZONE_INVALID"

        invalid_machine = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"machine_ids": "not-a-uuid"},
        )
        assert invalid_machine.status_code == 422, invalid_machine.text
        assert invalid_machine.json()["code"] == "TREND_FILTER_INVALID"

        outside = client.get(f"/api/v1/organizations/{uuid4()}/trend")
        assert outside.status_code == 403, outside.text
        assert outside.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"

        missing_machine = client.post(
            f"/api/v1/organizations/{organization.id}/trend/baselines",
            json={
                "machine_id": str(uuid4()),
                "metric_key": "output_factor",
                "unit": "%",
                "name": "Invalid",
                "baseline_value": 100,
                "effective_from": "2026-09-01T00:00:00Z",
            },
        )
        assert missing_machine.status_code == 404, missing_machine.text
        assert missing_machine.json()["code"] == "TREND_SOURCE_UNAVAILABLE"


def test_trend_rejects_invalid_baseline_and_maintenance_interval() -> None:
    with _workspace_client() as (client, organization):
        machine_id, _, _, _ = _seed_trend_data(client, organization.id)
        invalid_baseline = client.post(
            f"/api/v1/organizations/{organization.id}/trend/baselines",
            json={
                "machine_id": machine_id,
                "metric_key": "output_factor",
                "unit": "%",
                "name": "Invalid date range",
                "baseline_value": 100,
                "effective_from": "2026-09-10T00:00:00Z",
                "effective_to": "2026-09-01T00:00:00Z",
            },
        )
        assert invalid_baseline.status_code == 422, invalid_baseline.text
        assert invalid_baseline.json()["code"] == "TREND_BASELINE_INVALID"

        invalid_event = client.post(
            f"/api/v1/organizations/{organization.id}/trend/events",
            json={
                "machine_id": machine_id,
                "event_type": "SERVICE",
                "title": "Invalid interval",
                "started_at": "2026-09-06T03:00:00Z",
                "ended_at": "2026-09-06T01:00:00Z",
            },
        )
        assert invalid_event.status_code == 422, invalid_event.text
        assert invalid_event.json()["code"] == "MAINTENANCE_INTERVAL_INVALID"
