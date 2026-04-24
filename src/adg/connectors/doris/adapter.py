from adg.connectors.relational import RelationalConnector


class DorisConnector(RelationalConnector):
    """Doris connector that reuses the MySQL wire-protocol driver path."""

    connector_type = "doris"
    sqlalchemy_drivername = "mysql+pymysql"
    dependency_name = "pymysql"
    install_extra = "doris"
