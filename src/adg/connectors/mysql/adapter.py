from adg.connectors.relational import RelationalConnector


class MySqlConnector(RelationalConnector):
    connector_type = "mysql"
    sqlalchemy_drivername = "mysql+pymysql"
    dependency_name = "pymysql"
    install_extra = "mysql"
