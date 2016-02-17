import logging
import psycopg2

import pgpm.lib.utils
import pgpm.lib.utils.db
import pgpm.lib.version
import pgpm.lib.utils.config
import pgpm.lib.utils.vcs


class AbstractDeploymentManager(object):
    """
    "Abstract" class (not intended to be called directly) that sets basic configuration and interface for classes
    that manage deployments within db
    """
    def __init__(self, connection_string, pgpm_schema_name='_pgpm', logger=None):
        """
        initialises the manager and connects to the DB
        :param connection_string: connection string consumable by DBAPI 2.0
        :param pgpm_schema_name: name of pgpm schema (default '_pgpm')
        :param logger: logger object
        """
        self._logger = logger or logging.getLogger(__name__)
        self._connection_string = connection_string
        self._conn = psycopg2.connect(connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)
        self._conn.init(logger)
        self._pgpm_schema_name = pgpm_schema_name
        self._pgpm_version = pgpm.lib.utils.config.Version(pgpm.lib.version.__version__,
                                                           pgpm.lib.utils.config.VersionTypes.python)

    DEPLOYMENT_OUTPUT_CODE_OK = 0
    DEPLOYMENT_OUTPUT_CODE_NOT_ALL_DEPLOYED = 1
