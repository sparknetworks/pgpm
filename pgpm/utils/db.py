import psycopg2
import psycopg2.extensions
import logging


class MegaConnection(psycopg2.extensions.connection):
    """
    A connection that uses `MegaCursor` automatically.
    """
    def __init__(self, dsn, *more):
        super().__init__(dsn, *more)
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


class MegaCursor(psycopg2.extensions.cursor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.connection.__class__.__name__ != 'MegaConnection':
            raise self.connection.ProgrammingError(
                'MegaCursor can only be used with MegaConnection. Instead type "{0}" is used. '
                'Reinitialise db connection with correct class'.format(self.connection.__class__.__name__))

    def execute(self, query, args=None):
        try:
            return super(MegaCursor, self).execute(query, args)
        finally:
            self.connection.logger.debug('Executing query: {0}'.format(self.query.decode('utf-8')))
            noticies = self.connection.fetch_new_notices()
            if noticies:
                for notice in noticies:
                    self.connection.logger.debug(notice)

    def callproc(self, procname, args=None):
        try:
            return super(MegaCursor, self).callproc(procname, args)
        finally:
            self.connection.logger.debug('Calling stored procedure: {0}'.format(self.query.decode('utf-8')))
            noticies = self.connection.fetch_new_notices()
            if noticies:
                for notice in noticies:
                    self.connection.logger.debug(notice)

