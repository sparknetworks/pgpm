import os
import sys
import tempfile

import pytest
import shutil
import subprocess

import pgpm.lib.install
import pgpm.lib.deploy

import tests.conftest


def get_pgpm_path():
    """
    returns path to directory that contains pgpm module
    :return:
    """
    import pgpm
    import inspect

    main_path = os.path.dirname(os.path.dirname(inspect.getfile(pgpm)))
    return main_path


TEST_DIR_GIT_NAME = "test_dir_git"
TEST_DIR_NO_GIT_NAME = "test_dir_no_git"
TEST_SCHEMA_LOW_0_5_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_low_0_5_0"
TEST_SCHEMA_TOP_0_1_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_top_0_1_0"
TEST_SCHEMA_TOP_0_2_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_top_0_2_0"
TEST_CONFIG_FILE_NAME = "config.json"


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


@pytest.fixture(scope="module",
                params=[TEST_SCHEMA_LOW_0_5_0_PATH, TEST_SCHEMA_TOP_0_1_0_PATH, TEST_SCHEMA_TOP_0_2_0_PATH])
def deployment_manager(request):
    dm_instance = pgpm.lib.deploy.DeploymentManager("host={0} port={1} dbname={2} user={3} password={4}"
                                                                .format(os.environ['PGPM_TEST_DB_HOST'],
                                                                        os.environ['PGPM_TEST_DB_PORT'],
                                                                        os.environ['PGPM_TEST_DB_NAME'],
                                                                        os.environ['PGPM_TEST_USER_NAME'],
                                                                        os.environ['PGPM_TEST_USER_PASSWORD']),
                                                    request.param, os.path.join(request.param, TEST_CONFIG_FILE_NAME))
    return dm_instance
