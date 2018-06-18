import os
from hypothesistooling import git
import hypothesistooling as tools
import re
import sys
from datetime import datetime, timedelta
import subprocess
import shutil


PACKAGE_NAME = 'hypothesis-python'

HYPOTHESIS_PYTHON = os.path.join(tools.ROOT, PACKAGE_NAME)
PYTHON_TAG_PREFIX = 'hypothesis-python-'


BASE_DIR = HYPOTHESIS_PYTHON

PYTHON_SRC = os.path.join(HYPOTHESIS_PYTHON, 'src')
PYTHON_TESTS = os.path.join(HYPOTHESIS_PYTHON, 'tests')

RELEASE_FILE = os.path.join(HYPOTHESIS_PYTHON, 'RELEASE.rst')

assert os.path.exists(PYTHON_SRC)


__version__ = None
__version_info__ = None

VERSION_FILE = os.path.join(PYTHON_SRC, 'hypothesis/version.py')

with open(VERSION_FILE) as o:
    exec(o.read())


def has_release():
    return os.path.exists(RELEASE_FILE)


CHANGELOG_ANCHOR = re.compile(r"^\.\. _v\d+\.\d+\.\d+:$")
CHANGELOG_BORDER = re.compile(r"^-+$")
CHANGELOG_HEADER = re.compile(r"^\d+\.\d+\.\d+ - \d\d\d\d-\d\d-\d\d$")
RELEASE_TYPE = re.compile(r"^RELEASE_TYPE: +(major|minor|patch)")


MAJOR = 'major'
MINOR = 'minor'
PATCH = 'patch'

VALID_RELEASE_TYPES = (MAJOR, MINOR, PATCH)


def parse_release_file():
    with open(RELEASE_FILE) as i:
        release_contents = i.read()

    release_lines = release_contents.split('\n')

    m = RELEASE_TYPE.match(release_lines[0])
    if m is not None:
        release_type = m.group(1)
        if release_type not in VALID_RELEASE_TYPES:
            print('Unrecognised release type %r' % (release_type,))
            sys.exit(1)
        del release_lines[0]
        release_contents = '\n'.join(release_lines).strip()
    else:
        print(
            'RELEASE.rst does not start by specifying release type. The first '
            'line of the file should be RELEASE_TYPE: followed by one of '
            'major, minor, or patch, to specify the type of release that '
            'this is (i.e. which version number to increment). Instead the '
            'first line was %r' % (release_lines[0],)
        )
        sys.exit(1)

    return release_type, release_contents


def update_changelog_and_version():
    global __version_info__
    global __version__

    with open(CHANGELOG_FILE) as i:
        contents = i.read()
    assert '\r' not in contents
    lines = contents.split('\n')
    assert contents == '\n'.join(lines)
    for i, l in enumerate(lines):
        if CHANGELOG_ANCHOR.match(l):
            assert CHANGELOG_BORDER.match(lines[i + 2]), repr(lines[i + 2])
            assert CHANGELOG_HEADER.match(lines[i + 3]), repr(lines[i + 3])
            assert CHANGELOG_BORDER.match(lines[i + 4]), repr(lines[i + 4])
            beginning = '\n'.join(lines[:i])
            rest = '\n'.join(lines[i:])
            assert '\n'.join((beginning, rest)) == contents
            break

    release_type, release_contents = parse_release_file()

    new_version = list(__version_info__)
    bump = VALID_RELEASE_TYPES.index(release_type)
    new_version[bump] += 1
    for i in range(bump + 1, len(new_version)):
        new_version[i] = 0
    new_version = tuple(new_version)
    new_version_string = '.'.join(map(str, new_version))

    __version_info__ = new_version
    __version__ = new_version_string

    with open(VERSION_FILE) as i:
        version_lines = i.read().split('\n')

    for i, l in enumerate(version_lines):
        if 'version_info' in l:
            version_lines[i] = '__version_info__ = %r' % (new_version,)
            break

    with open(VERSION_FILE, 'w') as o:
        o.write('\n'.join(version_lines))

    now = datetime.utcnow()

    date = max([
        d.strftime('%Y-%m-%d') for d in (now, now + timedelta(hours=1))
    ])

    heading_for_new_version = ' - '.join((new_version_string, date))
    border_for_new_version = '-' * len(heading_for_new_version)

    new_changelog_parts = [
        beginning.strip(),
        '',
        '.. _v%s:' % (new_version_string),
        '',
        border_for_new_version,
        heading_for_new_version,
        border_for_new_version,
        '',
        release_contents,
        '',
        rest
    ]

    with open(CHANGELOG_FILE, 'w') as o:
        o.write('\n'.join(new_changelog_parts))


def update_for_pending_release():
    update_changelog_and_version()

    git('rm', RELEASE_FILE)
    git('add', CHANGELOG_FILE, VERSION_FILE)

    git(
        'commit', '-m',
        'Bump version to %s and update changelog\n\n[skip ci]' % (__version__,)
    )


def update_changelog_for_docs():
    if not tools.has_release():
        return
    if tools.has_uncommitted_changes(tools.CHANGELOG_FILE):
        print(
            'Cannot build documentation with uncommitted changes to '
            'changelog and a pending release. Please commit your changes or '
            'delete your release file.')
        sys.exit(1)
    tools.update_changelog_and_version()


CHANGELOG_FILE = os.path.join(HYPOTHESIS_PYTHON, 'docs', 'changes.rst')
DIST = os.path.join(HYPOTHESIS_PYTHON, 'dist')


def changelog():
    with open(CHANGELOG_FILE) as i:
        return i.read()


def build_distribution():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    subprocess.check_output([
        sys.executable, 'setup.py', 'sdist', '--dist-dir', DIST,
    ])


def upload_distribution():
    subprocess.check_call([
        sys.executable, '-m', 'twine', 'upload',
        '--config-file', tools.PYPIRC,
        os.path.join(DIST, '*'),
    ])


def latest_version():
    versions = []

    for t in tools.tags():
        if t.startswith(PYTHON_TAG_PREFIX):
            t = t[len(PYTHON_TAG_PREFIX):]
        else:
            continue
        assert t == t.strip()
        parts = t.split('.')
        assert len(parts) == 3
        v = tuple(map(int, parts))
        versions.append((v, t))

    _, latest = max(versions)

    return latest


def tag_name():
    return PYTHON_TAG_PREFIX + __version__
