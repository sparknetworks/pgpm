import os
import tempfile

import pytest
import shutil
import subprocess

import tests.conftest

TEST_DIR_GIT_NAME = "test_dir_git"
TEST_DIR_NO_GIT_NAME = "test_dir_no_git"


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


