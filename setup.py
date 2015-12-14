# Copyright (C) 2015 Affinitas GmbH
#
# This setup script is part of pgpm packcage and is released under
# the MIT License: http://opensource.org/licenses/MIT

import os
import re
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        errno = tox.cmdline(args=args)
        sys.exit(errno)


def get_version():
    """
    parse __init__.py for version number instead of importing the file
    see http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
    """
    version_file = os.path.join(PKG, 'lib/version.py')
    ver_str_line = open(version_file, "rt").read()
    version_regex = r'^__version__ = [\'"]([^\'"]*)[\'"]'
    mo = re.search(version_regex, ver_str_line, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError('Unable to find version string in %s.'
                           % (version_file,))


PKG = "pgpm"

VERSION = get_version()

setup(
    name='pgpm',
    version=VERSION,
    author='Artem Panchoyan',
    author_email='artem.panchoyan@gmail.com',
    description='Postgres package manager',
    license='MIT',
    keywords='postgres database package deploying',
    url='https://github.com/affinitas/pgpm',
    packages=['pgpm', 'pgpm.utils', 'pgpm.lib', 'pgpm.lib.utils'],
    long_description=open('README.rst').read(),
    install_requires=['docopt', 'psycopg2', 'sqlparse', 'colorama', 'chardet'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',
        'Topic :: Database'
    ],
    tests_require=[
        'tox'
    ],
    cmdclass={
        'test': Tox,
    },
    entry_points={
        'console_scripts': [
            'pgpm=pgpm.app:main',
        ],
    },
    package_data={
        'pgpm': [
            'lib/db_scripts/*.sql',
            'lib/db_scripts/functions/*',
            'lib/db_scripts/migrations/*'
        ]
    }
)
