import pytest
import os
import subprocess

import pgpm.lib.utils.vcs


def test_is_git_directory(vcs_dirs):
    """
    Testing is_git_directory
    :param vcs_dirs: paths to test directories. First one is git enabled, second one is not
    :return:
    """
    assert pgpm.lib.utils.vcs.is_git_directory(vcs_dirs[0]) == True
    assert pgpm.lib.utils.vcs.is_git_directory(vcs_dirs[1]) == False
    cwd = os.getcwd()
    os.chdir(vcs_dirs[0])
    assert pgpm.lib.utils.vcs.is_git_directory() == True
    os.chdir(cwd)
    os.chdir(vcs_dirs[1])
    assert pgpm.lib.utils.vcs.is_git_directory() == False


def test_get_git_revision_hash(vcs_dirs):
    """
    Test getting git hash
    :param vcs_dirs: paths to test directories. First one is git enabled, second one is not
    :return:
    """
    assert pgpm.lib.utils.vcs.get_git_revision_hash(vcs_dirs[0])
    with pytest.raises(subprocess.CalledProcessError):
        assert pgpm.lib.utils.vcs.get_git_revision_hash(vcs_dirs[1])


def test_find_whole_word():
    """
    Test find_whole_word function
    :return:
    """
    assert pgpm.lib.utils.find_whole_word("test")("Nothing") is None
    assert pgpm.lib.utils.find_whole_word("test")("Test").group().lower() == "test"
    assert pgpm.lib.utils.find_whole_word("test")("Test test One Two testing test").group().lower() == "test"
    assert pgpm.lib.utils.find_whole_word("test")("Testify") is None


def test_collect_scripts_from_sources():
    """
    Test collecting scripts from files function (collect_scripts_from_sources)
    :return:
    """
    assert 0
