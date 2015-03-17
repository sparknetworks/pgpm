from pgpm import _version
import distutils.version

PGPM_SCHEMA_NAME = "_pgpm"
PGPM_SCHEMA_SUBCLASS = "basic"
PGPM_VERSION = distutils.version.StrictVersion(_version.__version__)

CONFIG_FILE_NAME = "config.json"