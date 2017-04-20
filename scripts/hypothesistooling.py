import subprocess
import os


def current_branch():
    return subprocess.check_output([
        "git", "rev-parse", "--abbrev-ref", "HEAD"
    ]).decode('ascii').strip()


def tags():
    result = [t.decode('ascii') for t in subprocess.check_output([
        "git", "tag"
    ]).split(b"\n")]
    assert len(set(result)) == len(result)
    return set(result)


ROOT = subprocess.check_output([
    "git", "rev-parse", "--show-toplevel"]).decode('ascii').strip()
SRC = os.path.join(ROOT, "src")

assert os.path.exists(SRC)


__version__ = None


with open(os.path.join(ROOT, "src/hypothesis/version.py")) as o:
    exec(o.read())

assert __version__ is not None


def latest_version():
    versions = []

    for t in tags():
        # All versions get tags but not all tags are versions (and there are
        # a large number of historic tags with a different format for versions)
        # so we parse each tag as a triple of ints (MAJOR, MINOR, PATCH)
        # and skip any tag that doesn't match that.
        assert t == t.strip()
        parts = t.split(".")
        if len(parts) != 3:
            continue
        try:
            v = tuple(map(int, parts))
        except ValueError:
            continue

        versions.append((v, t))

    _, latest = max(versions)

    assert latest in tags()
    return latest


def changelog():
    with open(os.path.join(ROOT, "docs", "changes.rst")) as i:
        return i.read()


def has_source_changes(version):
    return subprocess.call([
        "git", "diff", "--exit-code", version, SRC,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0


def git(*args):
    subprocess.check_call(("git",) + args)


def create_tag():
    assert __version__ not in tags()
    git("config", "user.name", "Travis CI on behalf of David R. MacIver")
    git("config", "user.email", "david@drmaciver.com")
    git("config", "core.sshCommand", "ssh -i deploy_key")
    git("tag", __version__)
    git("push", "--tags")
