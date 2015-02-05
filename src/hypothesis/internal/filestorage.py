import os

__hypothesis_home_directory = None


def set_hypothesis_home_dir(directory):
    global __hypothesis_home_directory
    __hypothesis_home_directory = directory


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def hypothesis_home_dir():
    global __hypothesis_home_directory
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.getenv('HYPOTHESIS_STORAGE_DIRECTORY')
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.path.join(
            os.getcwd(), '.hypothesis'
        )
    mkdir_p(__hypothesis_home_directory)
    return __hypothesis_home_directory


def storage_directory(name):
    path = os.path.join(hypothesis_home_dir(), name)
    mkdir_p(path)
    return path
