import os
import sys
import tempfile

import psycopg2
import pytest
import shutil
import subprocess

import pgpm.lib.install
import pgpm.lib.deploy
import pgpm.lib.utils.db

import tests.conftest


TEST_DIR_GIT_NAME = "test_dir_git"
TEST_DIR_NO_GIT_NAME = "test_dir_no_git"

PGPM_TEST_USER_NAME = "pgpm_test_user"
PGPM_TEST_USER_PASSWORD = "pgpm_test_user_password"
PGPM_TEST_DB_HOST = "localhost"
PGPM_TEST_DB_PORT = "5432"
PGPM_TEST_DB_NAME = "pgpm_test"
PGPM_TEST_DB_NAME_1 = "pgpm_test_1"
PGPM_TEST_DB_NAME_2 = "pgpm_test_2"
PGPM_TEST_DB_NAME_3 = "pgpm_test_3"
PGPM_TEST_DB_NAME_4 = "pgpm_test_4"


@pytest.fixture(scope="module")
def vcs_dirs(request):
    git_dir_path = tempfile.mkdtemp(prefix=TEST_DIR_GIT_NAME)
    no_git_dir_path = tempfile.mkdtemp(prefix=TEST_DIR_NO_GIT_NAME)
    cwd = os.getcwd()
    os.chdir(git_dir_path)
    subprocess.call(["git", "init"])
    subprocess.call(["touch", "test_vcs_dirs"])
    subprocess.call(["git", "add", "."])
    subprocess.call(["git", "commit", "-am", "'commit to test git functionality'"])
    os.chdir(cwd)

    def fin():
        shutil.rmtree(git_dir_path)
        shutil.rmtree(no_git_dir_path)
    request.addfinalizer(fin)
    return git_dir_path, no_git_dir_path


@pytest.fixture(scope="module")
def installation_manager():
    im_instance = pgpm.lib.install.InstallationManager("host={0} port={1} dbname={2} user={3} password={4}"
                                                       .format(os.environ['PGPM_TEST_DB_HOST'],
                                                               os.environ['PGPM_TEST_DB_PORT'],
                                                               os.environ['PGPM_TEST_DB_NAME'],
                                                               os.environ['PGPM_TEST_USER_NAME'],
                                                               os.environ['PGPM_TEST_USER_PASSWORD']))
    return im_instance


@pytest.fixture(scope="module")
def deployment_manager(request):
    dm_instance = pgpm.lib.deploy.DeploymentManager("host={0} port={1} dbname={2} user={3} password={4}"
                                                    .format(os.environ['PGPM_TEST_DB_HOST'],
                                                            os.environ['PGPM_TEST_DB_PORT'],
                                                            os.environ['PGPM_TEST_DB_NAME'],
                                                            os.environ['PGPM_TEST_USER_NAME'],
                                                            os.environ['PGPM_TEST_USER_PASSWORD']))
    return dm_instance


@pytest.fixture(scope="module")
def single_db(request):
    conn = psycopg2.connect("host={0} port={1} dbname={2} user={3} password={4}"
                            .format(PGPM_TEST_DB_HOST,
                                    PGPM_TEST_DB_PORT,
                                    PGPM_TEST_DB_NAME,
                                    PGPM_TEST_USER_NAME,
                                    PGPM_TEST_USER_PASSWORD),
                            connection_factory=pgpm.lib.utils.db.MegaConnection)
    cur = conn.cursor()

    def fin():
        conn.close()
    request.addfinalizer(fin)

