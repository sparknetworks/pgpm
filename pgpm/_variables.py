from pgpm import _version
from pgpm.utils import config

PGPM_SCHEMA_NAME = "_pgpm"
PGPM_SCHEMA_SUBCLASS = "basic"
PGPM_VERSION = config.Version(_version.__version__, config.VersionTypes.python)

MIGRATIONS_FOLDER_NAME = "scripts/migrations"
CONFIG_FILE_NAME = "config.json"