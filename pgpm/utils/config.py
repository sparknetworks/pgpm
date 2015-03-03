import re


class SchemaConfiguration:
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
        self.version = Version(config_dict["version"])
        if "license" in config_dict:
            self.license = config_dict["license"]
        if "owner_role" in config_dict:
            self.owner_role = config_dict["owner_role"]
        if "user_roles" in config_dict:
            self.user_roles = config_dict["user_roles"]


class Version:
    """
    Version of schema
    """
    major = 0
    minor = 0
    patch = 0
    pre = None
    metadata = None

    def __init__(self, version_string):
        """
        Parses string version of pg schema written in a format similar to semver but "_" instead of "." is used
        :param version_string: string version of pg schema
        :return: tuple with major, minor, patch, pre and metadata
        """
        version_r = r'(\d{1,3})_(\d{1,3})_(\d{1,3})'
        version_list = re.compile(version_r, flags=re.IGNORECASE).findall(version_string)
        self.major = version_list[0][0]
        self.minor = version_list[0][1]
        self.patch = version_list[0][2]

    def to_string(self):
        """
        stringifies version
        :param version: Version
        :return: string of version
        """
        return '{0}_{1}_{2}'.format(self.major, self.minor, self.patch)