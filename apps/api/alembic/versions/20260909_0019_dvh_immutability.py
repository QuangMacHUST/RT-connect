"""Protect persisted P17 DVH snapshots from update and delete mutation.

Revision ID: 20260909_0019
Revises: 20260909_0018
Create Date: 2026-09-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260909_0019"
down_revision: str | Sequence[str] | None = "20260909_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_POSTGRES_FUNCTION = "rt_connect_reject_dvh_analysis_run_mutation"
_POSTGRES_TRIGGER = "trg_dvh_analysis_runs_immutable"
_SQLITE_UPDATE_TRIGGER = "trg_dvh_analysis_runs_immutable_update"
_SQLITE_DELETE_TRIGGER = "trg_dvh_analysis_runs_immutable_delete"


def upgrade() -> None:
    """Install a database-level append-only guard for DVH result snapshots."""

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            f"""
            CREATE OR REPLACE FUNCTION {_POSTGRES_FUNCTION}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $function$
            BEGIN
                RAISE EXCEPTION
                    'DVH_RUN_IMMUTABLE: persisted DVH analysis runs cannot be updated or deleted';
            END;
            $function$;
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {_POSTGRES_TRIGGER}
            BEFORE UPDATE OR DELETE ON dvh_analysis_runs
            FOR EACH ROW
            EXECUTE FUNCTION {_POSTGRES_FUNCTION}();
            """
        )
    elif dialect == "sqlite":
        # SQLite is used by the focused local tests.  Keep the direct SQL
        # invariant there as well; the ORM mapper guard covers normal ORM
        # mutations, while these triggers cover text/bulk UPDATE and DELETE.
        op.execute(
            f"""
            CREATE TRIGGER {_SQLITE_UPDATE_TRIGGER}
            BEFORE UPDATE ON dvh_analysis_runs
            BEGIN
                SELECT RAISE(ABORT,
                    'DVH_RUN_IMMUTABLE: persisted DVH analysis runs cannot be updated or deleted');
            END;
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {_SQLITE_DELETE_TRIGGER}
            BEFORE DELETE ON dvh_analysis_runs
            BEGIN
                SELECT RAISE(ABORT,
                    'DVH_RUN_IMMUTABLE: persisted DVH analysis runs cannot be updated or deleted');
            END;
            """
        )


def downgrade() -> None:
    """Remove the append-only guard before dropping or replacing the table."""

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS {_POSTGRES_TRIGGER} ON dvh_analysis_runs")
        op.execute(f"DROP FUNCTION IF EXISTS {_POSTGRES_FUNCTION}()")
    elif dialect == "sqlite":
        op.execute(f"DROP TRIGGER IF EXISTS {_SQLITE_DELETE_TRIGGER}")
        op.execute(f"DROP TRIGGER IF EXISTS {_SQLITE_UPDATE_TRIGGER}")
