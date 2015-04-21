import os
import subprocess


def is_git_directory(path='.'):
    return subprocess.call(['git', '-C', path, 'rev-parse --is-inside-work-tree'],
                           stderr=subprocess.STDOUT, stdout=open(os.devnull, 'w')) == 0