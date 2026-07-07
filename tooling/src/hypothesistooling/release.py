# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import requests
import tomli

from hypothesistooling import cargo
from hypothesistooling.cargo import CARGO_TOML
from hypothesistooling.git import ROOT, assert_can_release, git, has_changes
from hypothesistooling.scripts import pip_tool

PACKAGE_NAME = "hypothesis"

HYPOTHESIS = ROOT / PACKAGE_NAME

PYTHON_SRC = HYPOTHESIS / "src"
PYTHON_TESTS = HYPOTHESIS / "tests"
DOMAINS_LIST = PYTHON_SRC / "hypothesis" / "vendor" / "tlds-alpha-by-domain.txt"

RELEASE_FILE = HYPOTHESIS / "RELEASE.rst"
RELEASE_SAMPLE_FILE = HYPOTHESIS / "RELEASE-sample.rst"
CHANGELOG_FILE = HYPOTHESIS / "docs" / "changelog.rst"
DIST = HYPOTHESIS / "dist"

assert PYTHON_SRC.exists()


__version__ = tomli.loads(CARGO_TOML.read_text(encoding="utf-8"))["package"]["version"]
__version_info__ = tuple(int(p) for p in __version__.split("."))


__RELEASE_DATE_STRING = None


def release_date_string():
    """Returns a date string that represents what should be considered "today"
    for the purposes of releasing, and ensure that we don't change part way
    through a release."""
    global __RELEASE_DATE_STRING
    if __RELEASE_DATE_STRING is None:
        __RELEASE_DATE_STRING = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return __RELEASE_DATE_STRING


RELEASE_TYPE = re.compile(r"^RELEASE_TYPE: +(major|minor|patch)")
VALID_RELEASE_TYPES = ("major", "minor", "patch")


def has_release():
    return RELEASE_FILE.exists()


def has_release_sample():
    return RELEASE_SAMPLE_FILE.exists()


def parse_release_file():
    return parse_release_file_contents(
        RELEASE_FILE.read_text(encoding="utf-8"), RELEASE_FILE
    )


def parse_release_file_contents(release_contents, filename):
    release_lines = [l.rstrip() for l in release_contents.split("\n")]

    m = RELEASE_TYPE.match(release_lines[0])
    if m is not None:
        release_type = m.group(1)
        if release_type not in VALID_RELEASE_TYPES:
            raise ValueError(f"Unrecognised release type {release_type!r}")
        del release_lines[0]
        release_contents = "\n".join(release_lines).strip()
    else:
        raise ValueError(
            f"{filename} does not start by specifying release type. The first "
            "line of the file should be RELEASE_TYPE: followed by one of "
            "major, minor, or patch, to specify the type of release that "
            "this is (i.e. which version number to increment). Instead the "
            f"first line was {release_lines[0]!r}"
        )

    return release_type, release_contents


def bump_version_info(version_info, release_type):
    new_version = list(version_info)
    bump = VALID_RELEASE_TYPES.index(release_type)
    new_version[bump] += 1
    for i in range(bump + 1, len(new_version)):
        new_version[i] = 0
    new_version = tuple(new_version)
    new_version_string = ".".join(map(str, new_version))
    return new_version_string, new_version


def commit_pending_release():
    """Create a commit with the new release."""
    git("rm", RELEASE_FILE)
    git("add", "-u", HYPOTHESIS)

    git(
        "commit",
        "-m",
        f"Bump {PACKAGE_NAME} version to {current_version()} "
        "and update changelog\n\n[skip ci]",
    )


def has_source_changes():
    return has_changes([PYTHON_SRC])


def build_docs(*, builder="html", only=(), to=None):
    # See https://www.sphinx-doc.org/en/stable/man/sphinx-build.html
    pip_tool(
        "sphinx-build",
        "--fail-on-warning",
        "--show-traceback",
        "--fresh-env",
        "--builder",
        builder,
        "docs",
        "docs/_build/" + (builder if to is None else to),
        *only,
        cwd=HYPOTHESIS,
    )


CHANGELOG_ANCHOR = re.compile(r"^\.\. _v\d+\.\d+\.\d+:$", flags=re.MULTILINE)
CHANGELOG_BORDER = re.compile(r"^-+$", flags=re.MULTILINE)
CHANGELOG_HEADER = re.compile(
    r"^\d+\.\d+\.\d+ - \d\d\d\d-\d\d-\d\d$", flags=re.MULTILINE
)


def update_changelog_and_version():
    global __version_info__
    global __version__

    contents = changelog()
    assert "\r" not in contents
    lines = contents.split("\n")
    for i, l in enumerate(lines):
        if CHANGELOG_ANCHOR.match(l):
            assert CHANGELOG_BORDER.match(lines[i + 2]), repr(lines[i + 2])
            assert CHANGELOG_HEADER.match(lines[i + 3]), repr(lines[i + 3])
            assert CHANGELOG_BORDER.match(lines[i + 4]), repr(lines[i + 4])
            assert lines[i + 3].startswith(
                __version__
            ), f"{__version__=}   {lines[i + 3]=}"
            beginning = "\n".join(lines[:i])
            rest = "\n".join(lines[i:])
            assert f"{beginning}\n{rest}" == contents
            break

    release_type, release_contents = parse_release_file()

    new_version_string, new_version_info = bump_version_info(
        __version_info__, release_type
    )

    __version_info__ = new_version_info
    __version__ = new_version_string

    if release_type == "major":
        major, _, _ = __version_info__
        old = f"Hypothesis {major - 1}.x"
        beginning = beginning.replace(old, f"Hypothesis {major}.x")
        rest = "\n".join([old, len(old) * "=", "", rest])

    cargo.write_version(CARGO_TOML, new_version_string)

    heading_for_new_version = f"{new_version_string} - {release_date_string()}"
    border_for_new_version = "-" * len(heading_for_new_version)

    new_changelog_parts = [
        beginning.strip(),
        "",
        f".. _v{new_version_string}:",
        "",
        border_for_new_version,
        heading_for_new_version,
        border_for_new_version,
        "",
        release_contents,
        "",
        rest,
    ]

    CHANGELOG_FILE.write_text("\n".join(new_changelog_parts), encoding="utf-8")

    # Replace the `since="RELEASEDAY"` argument to `note_deprecation`
    # with today's date, to record it for future reference.
    before = 'since="RELEASEDAY"'
    after = before.replace("RELEASEDAY", release_date_string())
    for root, _, files in os.walk(PYTHON_SRC):
        for fname in (os.path.join(root, f) for f in files if f.endswith(".py")):
            with open(fname, encoding="utf-8") as f:
                contents = f.read()
            if before in contents:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(contents.replace(before, after))

    update_pyproject_toml()


def update_pyproject_toml():
    # manually write back these changes using regex instead of pulling in a
    # toml dependency for writing. tomli doesn't support writing, and
    # tomli-w doesn't support writing with comments.
    toml_p = HYPOTHESIS / "pyproject.toml"
    toml_data = tomli.loads(toml_p.read_text())
    extras = toml_data["project"]["optional-dependencies"]
    extras.pop("all")
    readme = (ROOT / "README.md").read_text()
    content = toml_p.read_text()
    content = re.sub(
        r'\[project\.readme\].*content-type = "text/markdown"',
        f'[project.readme]\ntext = """{readme}"""\ncontent-type = "text/markdown"',
        content,
        flags=re.DOTALL,
    )

    all_extras = sorted(set(sum(extras.values(), [])))
    all_extras = json.dumps(all_extras).replace("\n", "\\n")
    content = re.sub(
        r"^all = \[.*\]$",
        f"all = {all_extras}",
        content,
        flags=re.MULTILINE,
    )
    toml_p.write_text(content)


def changelog():
    return CHANGELOG_FILE.read_text(encoding="utf-8")


def check_artifact_versions(*, expected_version):
    # sanity check that the version in each artifact is what we expect
    # Artifact names look like:
    #   hypothesis-<version>-cp313-cp313-manylinux_2_17_x86_64.whl
    #   hypothesis-<version>.tar.gz
    pattern = re.compile(r"^hypothesis-(?P<version>[^-]+?)(?:-.+\.whl|\.tar\.gz)$")
    artifacts = sorted(DIST.iterdir())
    assert artifacts, f"no artifacts found in {DIST}"
    for f in artifacts:
        m = pattern.match(f.name)
        assert m is not None, f"{f.name}: unrecognised artifact filename"
        assert (
            m.group("version") == expected_version
        ), f"{f.name}: version {m.group('version')!r} != expected {expected_version!r}"


def upload_distribution_to_pypi(*, expected_version):
    assert_can_release()
    check_artifact_versions(expected_version=expected_version)

    # used for trusted publishing
    assert "ACTIONS_ID_TOKEN_REQUEST_TOKEN" in os.environ

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--skip-existing",
            os.path.join(DIST, "*"),
        ]
    )


def create_github_release():
    # Construct plain-text + markdown version of this changelog entry,
    # with link to canonical source.
    build_docs(builder="text", only=["docs/changelog.rst"])
    textfile = os.path.join(HYPOTHESIS, "docs", "_build", "text", "changelog.txt")
    with open(textfile, encoding="utf-8") as f:
        lines = f.readlines()
    entries = [i for i, l in enumerate(lines) if CHANGELOG_HEADER.match(l)]
    anchor = current_version().replace(".", "-")
    changelog_body = (
        "".join(lines[entries[0] + 2 : entries[1]]).strip()
        + "\n\n*[The canonical version of these notes (with links) is on readthedocs.]"
        f"(https://hypothesis.readthedocs.io/en/latest/changelog.html#v{anchor})*"
    )

    # Create a GitHub release, to trigger Zenodo DOI minting.  See
    # https://developer.github.com/v3/repos/releases/#create-a-release
    resp = requests.post(
        "https://api.github.com/repos/HypothesisWorks/hypothesis/releases",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "tag_name": tag_name(),
            "name": f"Hypothesis version {current_version()}",
            "body": changelog_body,
        },
        timeout=120,  # seconds
    )

    # TODO: work out why this is 404'ing despite success (?!?) and fix it
    try:
        resp.raise_for_status()
    except Exception:
        import traceback

        traceback.print_exc()


def compute_new_version():
    if not has_release():
        return None
    release_type, _ = parse_release_file()
    _, new_version_info = bump_version_info(__version_info__, release_type)
    return ".".join(str(p) for p in new_version_info)


def current_version():
    return __version__


def tag_name():
    return f"v{__version__}"


def get_autoupdate_message(domainlist_changed):
    if domainlist_changed:
        return (
            "This patch updates our vendored `list of top-level domains "
            "<https://www.iana.org/domains/root/db>`__,\nwhich is used by the "
            "provisional :func:`~hypothesis.provisional.domains` strategy.\n"
        )
    return (
        "This patch updates our autoformatting tools, "
        "improving our code style without any API changes."
    )
