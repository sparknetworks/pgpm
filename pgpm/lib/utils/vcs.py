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
    return dulwich.repo.Repo.discover(path).head()


def get_git_remote(path='.', remote='origin', type='Fetch'):
    """
    Get git remote url
    :param path: path to repo
    :param remote:
    :param type:
    :return: remote url or exception
    """
    repo = dulwich.repo.Repo.discover(path)
    str = subprocess.check_output(['git', '-C', path, 'remote', 'show', '-n', remote]).strip().decode('utf-8')
    str = str[str.find(type):]
    str = str[:str.find('\n')].split(' ')[-1]
    return str
