import hypothesis.internal.filestorage as fs
import os

previous_home_dir = None


def setup_function(function):
    global previous_home_dir
    previous_home_dir = fs.hypothesis_home_dir()
    fs.set_hypothesis_home_dir(None)


def teardown_function(function):
    global previous_home_dir
    fs.set_hypothesis_home_dir(previous_home_dir)
    previous_home_dir = None


def test_homedir_exists_automatically():
    assert os.path.exists(fs.hypothesis_home_dir())


def test_can_set_homedir_and_it_will_exist(tmpdir):
    fs.set_hypothesis_home_dir(str(tmpdir.mkdir("kittens")))
    d = fs.hypothesis_home_dir()
    assert "kittens" in d
    assert os.path.exists(d)


def test_will_pick_up_location_from_env(tmpdir):
    os.environ['HYPOTHESIS_STORAGE_DIRECTORY'] = str(tmpdir)
    assert fs.hypothesis_home_dir() == str(tmpdir)


def test_storage_directories_are_created_automatically(tmpdir):
    fs.set_hypothesis_home_dir(str(tmpdir))
    assert os.path.exists(fs.storage_directory("badgers"))
