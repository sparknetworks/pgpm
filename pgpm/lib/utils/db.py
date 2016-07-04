import psycopg2
import psycopg2.extensions
import logging
import re
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def parse_connection_string_psycopg2(connection_string):
    """
    parses psycopg2 consumable connection string
    :param connection_string:
    :return: return dictionary with connection string parts
    """
    conn_prepared = {}
    conn_parsed = urlparse(connection_string)
    if not conn_parsed.hostname:
        _re_dbstr = re.compile(r'\bhost=(?P<host>[0-9a-zA-Z_.!@#$%^&*()~]+)|'
                               r'dbname=(?P<dbname>[0-9a-zA-Z_.!@#$%^&*()~]+)|'
                               r'port=(?P<port>[0-9a-zA-Z_.!@#$%^&*()~]+)|'
                               r'user=(?P<user>[0-9a-zA-Z_.!@#$%^&*()~]+)|'
                               r'password=(?P<password>[0-9a-zA-Z_.!@#$%^&*()~]+)\b', re.IGNORECASE)
        for match in _re_dbstr.finditer(connection_string):
            match_dict = match.groupdict()
            if match_dict['host']:
                conn_prepared['host'] = match_dict['host']
            if match_dict['port']:
                conn_prepared['port'] = match_dict['port']
            if match_dict['dbname']:
                conn_prepared['dbname'] = match_dict['dbname']
            if match_dict['user']:
                conn_prepared['user'] = match_dict['user']
            if match_dict['password']:
                conn_prepared['password'] = match_dict['password']
    else:
        conn_prepared = {
            'host': conn_parsed.hostname,
            'port': conn_parsed.port,
            'dbname': conn_parsed.path,
            'user': conn_parsed.username,
            'password': conn_parsed.password
        }

    return conn_prepared


class MegaConnection(psycopg2.extensions.connection):
    """
    A connection that uses `MegaCursor` automatically.
    """
    def __init__(self, dsn, *more):
        psycopg2.extensions.connection.__init__(self, dsn, *more)
        self._last_notice_flushed_index = -1
        self.logger = logging.getLogger(__name__)

    def cursor(self, *args, **kwargs):
        kwargs.setdefault('cursor_factory', MegaCursor)
        return super(MegaConnection, self).cursor(*args, **kwargs)

    def fetch_new_notices(self):
        if len(self.notices) > self._last_notice_flushed_index + 1:
            unflushed_notices = self.notices[self._last_notice_flushed_index + 1:len(self.notices)]
            self._last_notice_flushed_index = len(self.notices) - 1
            return unflushed_notices
        else:
            return None

    def init(self, logger):
        """Initialize the connection to log to `!logger`.
        The `!logger` parameter is a Logger
        instance from the standard logging module.
        """
        self.logger = logger or self.logger

    def close(self, rollback=True):
        # rollback or commit only if connection has transaction in progress
        if self.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
            # need to do as some middlewares like pgBouncer incorrectly react to implicit rollback
            # see more here: http://initd.org/psycopg/docs/connection.html#connection.close
            if rollback:
                self.rollback()
                self.logger.debug('Active transaction rolled back.')
            else:
                self.commit()
                self.logger.debug('Active transaction committed.')
        r_value = super(MegaConnection, self).close()
        self.logger.debug('Connection closed.')
        return r_value


class MegaCursor(psycopg2.extensions.cursor):
    def __init__(self, *args, **kwargs):
        psycopg2.extensions.cursor.__init__(self, *args, **kwargs)
        if self.connection.__class__.__name__ != 'MegaConnection':
            raise self.connection.ProgrammingError(
                'MegaCursor can only be used with MegaConnection. Instead type "{0}" is used. '
                'Reinitialise db connection with correct class'.format(self.connection.__class__.__name__))

    def execute(self, query, args=None):
        try:
            return super(MegaCursor, self).execute(query, args)
        except Exception:
            raise
        finally:
            self.connection.logger.debug('Executed query: {0}'.format(self.query))
            noticies = self.connection.fetch_new_notices()
            if noticies:
                for notice in noticies:
                    self.connection.logger.debug(notice)

    def callproc(self, procname, args=None):
        try:
            return super(MegaCursor, self).callproc(procname, args)
        except Exception:
            raise
        finally:
            self.connection.logger.debug('Called stored procedure: {0}'.format(self.query.decode('utf-8')))
            noticies = self.connection.fetch_new_notices()
            if noticies:
                for notice in noticies:
                    self.connection.logger.debug(notice)

    def close(self):
        r_value = super(MegaCursor, self).close()
        self.connection.logger.debug('Cursor closed.')
        return r_value


class SqlScriptsHelper:
    current_user_sql = 'select * from CURRENT_USER;'
    is_superuser_sql = 'select usesuper from pg_user where usename = CURRENT_USER;'

    @classmethod
    def get_pgpm_db_version(cls, cur, schema_name='_pgpm'):
        """
        returns current version of pgpm schema
        :return: tuple of major, minor and patch components of version
        """
        cls.set_search_path(cur, schema_name)
        cur.execute("SELECT _find_schema('{0}', '{1}')"
                    .format(schema_name, 'x'))
        # TODO: make it work with the way it's written below. currently throws error as func returns record
        # without column list
        # cur.callproc('_find_schema', [schema_name, 'x'])
        pgpm_v_ext = tuple(cur.fetchone()[0][1:-1].split(','))

        return pgpm_v_ext[2], pgpm_v_ext[3], pgpm_v_ext[4]

    @classmethod
    def create_db_schema(cls, cur, schema_name):
        """
        Create Postgres schema script and execute it on cursor
        """
        create_schema_script = "CREATE SCHEMA {0} ;\n".format(schema_name)
        cur.execute(create_schema_script)

    @classmethod
    def grant_usage_privileges(cls, cur, schema_name, roles):
        """
        Sets search path
        """
        cur.execute('GRANT USAGE ON SCHEMA {0} TO {1};'
                    'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {0} TO {1};'
                    .format(schema_name, roles))

    @classmethod
    def grant_usage_install_privileges(cls, cur, schema_name, roles):
        """
        Sets search path
        """
        cur.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {0} TO {1};'
                    'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {0} TO {1};'
                    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {0} TO {1};'
                    .format(schema_name, roles))

    @classmethod
    def grant_default_usage_install_privileges(cls, cur, schema_name, roles):
        """
        Sets search path
        """
        cur.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA {0} '
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {1};'
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA {0} GRANT EXECUTE ON FUNCTIONS TO {1};'
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA {0} '
                    'GRANT USAGE, SELECT ON SEQUENCES TO {1};'
                    .format(schema_name, roles))

    @classmethod
    def revoke_all(cls, cur, schema_name, roles):
        """
        Revoke all privileges from schema, tables, sequences and functions for a specific role
        """
        cur.execute('REVOKE ALL ON SCHEMA {0} FROM {1};'
                    'REVOKE ALL ON ALL TABLES IN SCHEMA {0} FROM {1};'
                    'REVOKE ALL ON ALL SEQUENCES IN SCHEMA {0} FROM {1};'
                    'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {0} FROM {1};'.format(schema_name, roles))

    @classmethod
    def set_search_path(cls, cur, schema_name):
        """
        Sets search path
        """
        cur.execute('set search_path TO {0}, public;'
                    .format(schema_name))

    @classmethod
    def schema_exists(cls, cur, schema_name):
        """
        Check if schema exists
        """
        cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{0}');"
                    .format(schema_name))
        return cur.fetchone()[0]