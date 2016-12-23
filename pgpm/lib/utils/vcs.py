import os
import subprocess
import dulwich.repo
import dulwich.errors


def is_git_directory(path='.'):
    """
    Checks if given directory is a git repository
    :param path: path to check
    :return: True if it's a git repo and False otherwise
    """
    try:
        dulwich.repo.Repo.discover(path)
    except dulwich.errors.NotGitRepository:
        return False

    return True


def get_git_revision_hash(path='.'):
    """
    Get git HEAD hash
    :param path: path to repo
    :return: hash or exception
    """
    return dulwich.repo.Repo.discover(path).head().decode("utf-8")


def get_git_remote_url(path='.', remote='origin'):
    """
    Get git remote url
    :param path: path to repo
    :param remote:
    :return: remote url or exception
    """
    return dulwich.repo.Repo.discover(path).get_config()\
        .get((b'remote', remote.encode('utf-8')), b'url').decode('utf-8')
