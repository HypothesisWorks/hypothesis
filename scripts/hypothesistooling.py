import subprocess
import os
from distutils.version import StrictVersion


def current_branch():
    return subprocess.check_output([
        "git", "rev-parse", "--abbrev-ref", "HEAD"
    ]).decode('ascii')


def tags():
    result = [t.decode('ascii') for t in subprocess.check_output([
        "git", "tag"
    ]).split(b"\n")]
    assert len(set(result)) == len(result)
    return set(result)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


__version__ = None


with open(os.path.join(ROOT, "src/hypothesis/version.py")) as o:
    exec(o.read())

assert __version__ is not None


def latest_version():
    versions = []

    for t in tags():
        try:
            versions.append((StrictVersion(t), t))
        except ValueError:
            pass

    _, latest = max(versions)

    assert latest in tags()
    return latest


def changelog():
    with open(os.path.join(ROOT, "docs", "changes.rst")) as i:
        return i.read()


DEVNULL = open(os.devnull)


def has_source_changes(version):
    return subprocess.call([
        "git", "diff", "--exit-code", version, SRC,
    ], stdout=DEVNULL, stderr=DEVNULL) != 0


def create_tag():
    assert __version__ not in tags()
    subprocess.check_call([
        "git", "tag", __version__
    ])
    subprocess.check_call([
        "git", "push", "--tags"
    ])
