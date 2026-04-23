from adg.connectors.relational import RelationalConnector


class DorisConnector(RelationalConnector):
    connector_type = "doris"
    sqlalchemy_drivername = "mysql+pymysql"
    dependency_name = "pymysql"
    install_extra = "doris"
