"""Synthetic development seed; never run against pilot or production without review."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from rt_connect_api.db.models import Machine, Organization, Site


def seed_synthetic_foundation(session: Session) -> None:
    organization = session.scalar(
        select(Organization).where(Organization.name == "Synthetic Oncology Center")
    )
    if organization is not None:
        return
    organization = Organization(name="Synthetic Oncology Center")
    site = Site(name="Synthetic Main Campus", organization=organization)
    session.add_all([organization, site])
    session.flush()
    machine = Machine(
        organization_id=organization.id,
        site=site,
        stable_machine_id="SYN-LINAC-01",
        display_name="Synthetic Linac 01",
    )
    session.add(machine)
    session.commit()
