# Copyright (C) 2015 Affinitas GmbH
#
# This setup script is part of dpm packcage and is released under
# the MIT License: http://opensource.org/licenses/MIT

import os
import re
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

def get_version():
    """parse __init__.py for version number instead of importing the file
    see http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
    """
    VERSIONFILE = os.path.join(PKG, '_version.py')
    verstrline = open(VERSIONFILE, "rt").read()
    VSRE = r'^__version__ = [\'"]([^\'"]*)[\'"]'
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError('Unable to find version string in %s.'
                           % (VERSIONFILE,))


PKG = "dpm"

VERSION = get_version()

class PyTestCommand(TestCommand):
    """ Command to run unit py.test unit tests
    """
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run(self):
        import pytest
        rcode = pytest.main(self.test_args)
        sys.exit(rcode)


setup(
    name='dpm',
    version=VERSION,
    author='Artem Panchoyan',
    author_email='artem.panchoyan@gmail.com',
    description='Postgres package manager',
    license='MIT',
    keywords='postgres database package deploying',
    url='https://github.com/affinitas/dpm',
    packages=['dpm'],
    long_description=open('README.rst').read(),
    install_requires  = ['docopt', 'psycopg2', 'sqlparse'],
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
            'pytest',
        ],
    cmdclass={
            'test': PyTestCommand,
        },
    entry_points={
        'console_scripts': [
            'dpm=dpm.deploy:main',
        ],
    },
    package_data={
        'dpm': ['scripts/*']
    }    
)