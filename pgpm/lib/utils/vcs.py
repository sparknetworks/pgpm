import os
import subprocess


def is_git_directory(path='.'):
    """
    Checks if given directory is a git repository
    :param path: path to check
    :return: True if it's a git repo and False otherwise
    """
    if path and subprocess.call(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'],
                           stderr=subprocess.STDOUT, stdout=open(os.devnull, 'w')) == 0:
        return True
    else:
        return False


def get_git_revision_hash(path='.'):
    """
    Get git HEAD hash
    :param path: path to repo
    :return: hash or exception
    """
    return subprocess.check_output(['git', '-C', path, 'rev-parse', 'HEAD']).strip().decode('utf-8')


def get_git_remote(path='.', remote='origin', type='Fetch'):
    """
    Get git remote url
    :param path: path to repo
    :param remote:
    :param type:
    :return: remote url or exception
    """
    str = subprocess.check_output(['git', '-C', path, 'remote', 'show', '-n', remote]).strip().decode('utf-8')
    str = str[str.find(type):]
    str = str[:str.find('\n')].split(' ')[-1]
    return str
