# RT-CONNECT API

Run commands from this directory after following the repository setup guide.

The API is a FastAPI service. P1 supplies only the platform boundaries: configuration,
health/readiness/version, correlation IDs, redacted structured logging, SQLAlchemy and
an Alembic baseline. Clinical modules are added in later phases.
