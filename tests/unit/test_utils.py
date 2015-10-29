import pytest
import os
import subprocess

import pgpm.lib.utils.vcs


def test_is_git_directory(vcs_dirs):
    assert pgpm.lib.utils.vcs.is_git_directory(vcs_dirs[0]) == True
    assert pgpm.lib.utils.vcs.is_git_directory(vcs_dirs[1]) == False
    cwd = os.getcwd()
    os.chdir(vcs_dirs[0])
    assert pgpm.lib.utils.vcs.is_git_directory() == True
    os.chdir(cwd)
    os.chdir(vcs_dirs[1])
    assert pgpm.lib.utils.vcs.is_git_directory() == False


def test_get_git_revision_hash(vcs_dirs):
    assert pgpm.lib.utils.vcs.get_git_revision_hash(vcs_dirs[0])
    with pytest.raises(subprocess.CalledProcessError):
        assert pgpm.lib.utils.vcs.get_git_revision_hash(vcs_dirs[1])


def test_find_whole_word():
    assert pgpm.lib.utils.find_whole_word("test")("Nothing")
