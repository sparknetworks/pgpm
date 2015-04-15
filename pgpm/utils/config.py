import re


class SchemaConfiguration(object):
    """
    stores properties of schema configuration
    """
    description = ""
    license = ""
    owner_role = ""
    user_roles = []

    def __init__(self, config_dict):
        """
        populates properties with cofig data
        """
        self.name = config_dict["name"]
        if "description" in config_dict:
            self.description = config_dict["description"]
        self.subclass = config_dict["subclass"]
        self.version = Version(config_dict["version"], VersionTypes.postgres)
        if "license" in config_dict:
            self.license = config_dict["license"]
        if "owner_role" in config_dict:
            self.owner_role = config_dict["owner_role"]
        if "user_roles" in config_dict:
            self.user_roles = config_dict["user_roles"]
        if "dependencies" in config_dict:
            self.dependencies = config_dict["dependencies"]


class VersionTypes(object):
    """
    Version types
    """
    postgres = 'postgres'
    semver = 'semver'
    x_postgres = 'x_postgres'
    x_semver = 'x_semver'
    python = 'python'


class Version(object):
    """
    Version of schema
    """
    major = 0
    minor = 0
    patch = 0
    pre = None
    metadata = None
    raw = ''

    def __init__(self, version_string, version_type=VersionTypes.postgres):
        """
        Parses string version of pg schema written in a format similar to semver but "_" instead of "." is used
        :param version_string: string version of pg schema
        :param version_type: type of version string. Defaults to postgres
        :return: tuple with major, minor, patch, pre and metadata
        """

        self.raw = version_string
        if version_type == VersionTypes.postgres:
            version_r = r'^(?P<major>\d+)_(?P<minor>\d+)_(?P<patch>\d+)'
            version_list = re.compile(version_r, flags=re.IGNORECASE).findall(version_string)
            self.major = int(version_list[0][0])
            self.minor = int(version_list[0][1])
            self.patch = int(version_list[0][2])
        elif version_type == VersionTypes.x_postgres:
            version_r = r'^(?P<major>\d+|x+)_(?P<minor>\d+|x+)_(?P<patch>\d+|x+)'
            version_list = re.compile(version_r, flags=re.IGNORECASE).findall(version_string)
            if "".join(set(version_list[0][0])).lower() == 'x':
                self.major = -1
            else:
                self.major = int(version_list[0][0])
            if "".join(set(version_list[0][1])).lower() == 'x':
                self.minor = -1
            else:
                self.minor = int(version_list[0][1])
            if "".join(set(version_list[0][2])).lower() == 'x':
                self.patch = -1
            else:
                self.patch = int(version_list[0][2])
        elif version_type == VersionTypes.python:
            # Implementation from http://svn.python.org/projects/python/branches/pep-0384/Lib/distutils/version.py
            version_r = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$', re.VERBOSE)
            version_match = version_r.match(version_string)
            if not version_match:
                raise ValueError("invalid version number '%s'" % version_string)

            (self.major, self.minor, self.patch, self.pre, self.metadata) = version_match.group(1, 2, 4, 5, 6)
        elif version_type == VersionTypes.semver:
            pass  # TODO: implement
        else:
            raise ValueError('version_type must be of VersionTypes values')

    def to_string(self):
        """
        stringifies version
        :return: string of version
        """
        if self.major == -1:
            major_str = 'x'
        else:
            major_str = self.major
        if self.minor == -1:
            minor_str = 'x'
        else:
            minor_str = self.minor
        if self.patch == -1:
            patch_str = 'x'
        else:
            patch_str = self.patch
        return '{0}_{1}_{2}'.format(major_str, minor_str, patch_str)