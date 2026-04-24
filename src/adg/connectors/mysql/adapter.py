from adg.connectors.relational import RelationalConnector


class MySqlConnector(RelationalConnector):
    """MySQL connector using SQLAlchemy's PyMySQL dialect."""

    connector_type = "mysql"
    sqlalchemy_drivername = "mysql+pymysql"
    dependency_name = "pymysql"
    install_extra = "mysql"
