from adg.connectors.relational import RelationalConnector


class PostgresConnector(RelationalConnector):
    connector_type = "postgres"
    sqlalchemy_drivername = "postgresql+psycopg"
    dependency_name = "psycopg"
    install_extra = "postgres"
