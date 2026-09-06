from collections.abc import Generator
from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from rt_connect_api.core.config import Settings
from rt_connect_api.db.base import Base
from rt_connect_api.db.models import (
    Machine,
    Organization,
    OrganizationMembership,
    Site,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.main import create_app
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity


@contextmanager
def _workspace_client(
    with_membership: bool = True,
) -> Generator[tuple[TestClient, Organization]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        organization = Organization(name="Synthetic Oncology Center")
        site = Site(name="Synthetic Main Campus", organization=organization)
        user_identity = UserIdentity(
            supabase_user_id="synthetic-supabase-subject",
            email="synthetic.user@example.invalid",
        )
        session.add_all([organization, site, user_identity])
        session.flush()
        machine = Machine(
            organization_id=organization.id,
            site_id=site.id,
            stable_machine_id="SYN-LINAC-01",
            display_name="Synthetic Linac 01",
        )
        session.add(machine)
        if with_membership:
            session.add(
                OrganizationMembership(
                    organization=organization,
                    user_identity=user_identity,
                )
            )
        session.commit()

    app = create_app(Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:"))
    app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
        subject="synthetic-supabase-subject",
        email="synthetic.user@example.invalid",
        claims={"sub": "synthetic-supabase-subject"},
    )

    def override_session() -> Generator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client, organization
    finally:
        engine.dispose()


def test_bootstrap_and_dashboard_use_server_resolved_organization_context() -> None:
    with _workspace_client() as (client, organization):
        bootstrap = client.get("/api/v1/session/bootstrap")
        dashboard = client.get(f"/api/v1/organizations/{organization.id}/dashboard")

    assert bootstrap.status_code == 200
    assert bootstrap.json() == {
        "subject": "synthetic-supabase-subject",
        "email": "synthetic.user@example.invalid",
        "organization": {"id": str(organization.id), "name": "Synthetic Oncology Center"},
    }
    assert dashboard.status_code == 200
    assert dashboard.json() == {
        "organization": {"id": str(organization.id), "name": "Synthetic Oncology Center"},
        "site_count": 1,
        "machine_count": 1,
        "recent_qa_count": 0,
        "active_job_count": 0,
        "warnings": [],
    }


def test_dashboard_rejects_client_requested_organization_outside_membership() -> None:
    with _workspace_client() as (client, _):
        response = client.get(f"/api/v1/organizations/{uuid4()}/dashboard")

    assert response.status_code == 403
    assert response.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_bootstrap_rejects_identity_without_active_membership() -> None:
    with _workspace_client(with_membership=False) as (client, _):
        response = client.get("/api/v1/session/bootstrap")

    assert response.status_code == 403
    assert response.json()["code"] == "ORGANIZATION_MEMBERSHIP_REQUIRED"
