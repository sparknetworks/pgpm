from pgpm.lib.utils import config
from pgpm.lib import version

__version__ = version.__version__

PGPM_SCHEMA_NAME = '_pgpm'
PGPM_SCHEMA_SUBCLASS = 'basic'
PGPM_VERSION = config.Version(__version__, config.VersionTypes.python)

MIGRATIONS_FOLDER_NAME = 'lib/db_scripts/migrations'
CONFIG_FILE_NAME = 'config.json'

LOGGING_FORMATTER = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
