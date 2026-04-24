from adg.connectors.relational import RelationalConnector


class PostgresConnector(RelationalConnector):
    """PostgreSQL connector using SQLAlchemy's psycopg dialect."""

    connector_type = "postgres"
    sqlalchemy_drivername = "postgresql+psycopg"
    dependency_name = "psycopg"
    install_extra = "postgres"
