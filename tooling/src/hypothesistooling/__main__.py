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
import pathlib
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from textwrap import indent

import requests
from coverage.config import CoverageConfig

from hypothesistooling import installers as install
from hypothesistooling.git import (
    IS_PULL_REQUEST,
    REPO_TESTS,
    ROOT,
    all_files,
    configure_git,
    create_tag,
    has_changes,
    modified_files,
    push_tag,
)
from hypothesistooling.release import (
    DOMAINS_LIST,
    HYPOTHESIS,
    PYTHON_SRC,
    PYTHON_TESTS,
    RELEASE_FILE,
    build_docs,
    commit_pending_release,
    compute_new_version,
    create_github_release,
    get_autoupdate_message,
    has_release,
    tag_name,
    update_changelog_and_version,
    upload_distribution_to_pypi,
)
from hypothesistooling.scripts import pip_tool

TASKS = {}
BUILD_FILES = tuple(
    os.path.join(ROOT, f)
    for f in ["tooling", "requirements", ".github", "hypothesis/tox.ini"]
)
TODAY = date.today().isoformat()


def task(if_changed=()):
    if not isinstance(if_changed, tuple):
        if_changed = (if_changed,)

    def accept(fn):
        def wrapped(*args, **kwargs):
            if if_changed and IS_PULL_REQUEST:
                if not has_changes(if_changed + BUILD_FILES):
                    changed = ", ".join(map(str, if_changed))
                    print(f"Skipping task due to no changes in {changed}")
                    return
            fn(*args, **kwargs)

        wrapped.__name__ = fn.__name__
        name = fn.__name__.replace("_", "-")
        if name != "<lambda>":
            TASKS[name] = wrapped
        return wrapped

    return accept


@task()
def check_installed():
    """No-op task that can be used to test for a successful install (so we
    don't fail to run if a previous install failed midway)."""


def codespell(*files):
    pip_tool(
        "codespell",
        "--check-hidden",
        "--check-filenames",
        "--ignore-words=./tooling/codespell-ignore.txt",
        # passing a custom --dictionary disables the default dictionary by default.
        # Add it back in with --dictionary=-.
        "--dictionary=-",
        "--dictionary=./tooling/codespell-dict.txt",
        "--skip=__pycache__,.mypy_cache,.venv,.git,tlds-alpha-by-domain.txt",
        *files,
    )


@task()
def lint():
    pip_tool("ruff", "check", ".")
    codespell(*(p for p in all_files() if not p.name.endswith("by-domain.txt")))

    failed = False

    matches = subprocess.run(
        r"git grep -En '@(dataclasses\.)?dataclass\(.*\)' "
        "| grep -Ev 'frozen=.*slots=|slots=.*frozen='",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout
    if matches:
        print("\nAll dataclass decorators must pass slots= and frozen= arguments:")
        print(indent(matches, "    "))
        failed = True

    matches = subprocess.run(
        r"git grep -nP '\b(the|as|a|to|because|user|test|about|from|only)\s+\1\b'",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout
    if matches:
        print("\nFound duplicate words:")
        print(indent(matches, "    "))
        failed = True

    if failed:
        sys.exit(1)


def do_publish():
    if not has_release():
        print("No release")
        return

    os.chdir(HYPOTHESIS)

    new_version = compute_new_version()

    print("Updating changelog and version")
    update_changelog_and_version()

    print("Committing changes")
    commit_pending_release()

    tag = tag_name()
    print(f"Creating tag {tag}")
    create_tag(tag)
    push_tag(tag)

    print("Uploading distribution to PyPI")
    upload_distribution_to_pypi(expected_version=new_version)

    print("Creating GitHub release")
    create_github_release()


@task()
def print_next_version():
    print(json.dumps({"new_version": compute_new_version()}))


@task()
def publish():
    # used for trusted publishing to PyPI
    if "ACTIONS_ID_TOKEN_REQUEST_TOKEN" not in os.environ:
        sys.exit("ACTIONS_ID_TOKEN_REQUEST_TOKEN is required for publish")
    if "GH_TOKEN" not in os.environ:
        sys.exit("GH_TOKEN is required for publish (used to create GitHub release)")

    configure_git()
    do_publish()
    sys.exit(0)


# See https://www.linuxfoundation.org/blog/copyright-notices-in-open-source-software-projects/
HEADER = """
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
""".strip()

RUST_HEADER = HEADER.replace("#", "//")

# this pattern is copied from shed
# https://github.com/Zac-HD/shed/blob/6471da71c5b5cc443443ef5ed072799db275e7c0/src/shed/__init__.py#L297
rst_pattern = re.compile(
    r"(?P<before>"
    r"^(?P<indent> *)\.\. "
    r"(?P<block>jupyter-execute::|"
    r"invisible-code-block: python|"  # magic rst comment for Sybil doctests
    r"(code|code-block|sourcecode|ipython):: (python|py|sage|python3|py3|numpy))\n"
    r"((?P=indent) +:.*\n)*"
    r"\n*"
    r")"
    r"(?P<code>(^((?P=indent) +.*)?\n)+)",
    flags=re.MULTILINE,
)


def remove_consecutive_newlines_in_rst(path: Path):
    # replace 2+ empty lines in `.. code-block:: python` blocks with just one empty
    # line
    content = path.read_text()
    processed_content = rst_pattern.sub(
        lambda m: m["before"] + re.sub(r"\n{3,}", "\n\n", m["code"]), content
    )
    if processed_content != content:
        path.write_text(processed_content)


@task()
def format(*, format_all=False):
    changed = modified_files()

    format_all = format_all or os.environ.get("FORMAT_ALL", "").lower() == "true"
    if "requirements/tools.txt" in changed:
        # We've changed the tools, which includes a lot of our formatting
        # logic, so we need to rerun formatters.
        format_all = True

    paths = all_files() if format_all else changed

    doc_paths_to_format = [p for p in sorted(paths) if p.suffix in {".rst", ".md"}]
    py_paths_to_format = [p for p in sorted(paths) if p.suffix == ".py"]
    rust_paths_to_format = [p for p in sorted(paths) if p.suffix == ".rs"]

    if not (py_paths_to_format or rust_paths_to_format or doc_paths_to_format):
        return

    # .coveragerc lists several regex patterns to treat as nocover pragmas, and
    # we want to find (and delete) cases where # pragma: no cover is redundant.
    def warn(msg):
        raise Exception(msg)

    config = CoverageConfig()
    config.from_file(os.path.join(HYPOTHESIS, ".coveragerc"), warn=warn, our_file=True)
    pattern = "|".join(l for l in config.exclude_list if "pragma" not in l)
    unused_pragma_pattern = re.compile(f"(({pattern}).*)  # pragma: no (branch|cover)")

    for p, header in [
        *((p, HEADER) for p in py_paths_to_format),
        *((p, RUST_HEADER) for p in rust_paths_to_format),
    ]:
        last_header_line = header.splitlines()[-1].rstrip()
        lines = []
        with open(p, encoding="utf-8") as fp:
            shebang = None
            first = True
            in_header = True
            for l in fp:
                if first:
                    first = False
                    if l[:2] == "#!":
                        shebang = l
                        continue
                elif in_header and l.rstrip() == last_header_line:
                    in_header = False
                    lines = []
                else:
                    lines.append(unused_pragma_pattern.sub(r"\1", l))

        source = "".join(lines).strip()
        with open(p, "w", encoding="utf-8") as fp:
            if shebang is not None:
                fp.write(shebang)
                fp.write("\n")
            fp.write(header)
            if source:
                fp.write("\n\n")
                fp.write(source)
            fp.write("\n")

    codespell(
        "--write-changes",
        *py_paths_to_format,
        *rust_paths_to_format,
        *doc_paths_to_format,
    )
    pip_tool("ruff", "check", "--fix-only", ".")
    pip_tool("shed", "--py310-plus", *py_paths_to_format, *doc_paths_to_format)

    for p in doc_paths_to_format:
        remove_consecutive_newlines_in_rst(p)


VALID_STARTS = {
    ".py": (HEADER.split()[0], "#!/usr/bin/env python"),
    ".rs": (RUST_HEADER.split()[0],),
}


@task()
def check_format():
    # In CI, where latency matters less, reformat every file rather than only
    # the changed ones, so that formatter upgrades can't leave stale formatting
    # lurking in untouched files until they're next edited.
    format(format_all=bool(os.environ.get("CI")))
    n = max(len(s) for starts in VALID_STARTS.values() for s in starts)
    bad = False
    for p in all_files():
        valid_starts = VALID_STARTS.get(p.suffix)
        if valid_starts is None:
            continue
        with open(p, encoding="utf-8") as fp:
            start = fp.read(n)
            if not any(start.startswith(s) for s in valid_starts):
                print(f"{p} has incorrect start {start!r}", file=sys.stderr)
                bad = True
    assert not bad
    try:
        check_not_changed()
    except Exception:
        box_width = 50
        inner_width = box_width - 2
        content_width = inner_width - 2
        msg1 = "Note: code differed after formatting."
        msg2 = "To fix this, run:"
        msg3 = "    ./build.sh format"

        lines = [
            "",
            "    " + "*" * box_width,
            "    *" + " " * inner_width + "*",
            "    *  " + msg1 + " " * (content_width - len(msg1)) + "*",
            "    *" + " " * inner_width + "*",
            "    *  " + msg2 + " " * (content_width - len(msg2)) + "*",
            "    *" + " " * inner_width + "*",
            "    *  " + msg3 + " " * (content_width - len(msg3)) + "*",
            "    *" + " " * inner_width + "*",
            "    " + "*" * box_width,
            "",
        ]
        print("\n".join(lines), file=sys.stderr)
        raise


def check_not_changed():
    subprocess.check_call(["git", "diff", "--exit-code"])


@task()
def compile_requirements(*, upgrade=False):
    if upgrade:
        extra = ["--upgrade", "--rebuild"]
    else:
        extra = []

    for f in Path("requirements").glob("*.in"):
        out_file = f.with_suffix(".txt")
        pip_tool(
            "pip-compile",
            "--allow-unsafe",  # future default, not actually unsafe
            "--resolver=backtracking",  # new pip resolver, default in pip-compile 7+
            *extra,
            str(f),
            "hypothesis/pyproject.toml",
            "--output-file",
            str(out_file),
            cwd=ROOT,
            env={
                "CUSTOM_COMPILE_COMMAND": "./build.sh upgrade-requirements",
                **os.environ,
            },
        )
        # Check that we haven't added anything to output files without adding to inputs
        out_pkgs = out_file.read_text(encoding="utf-8")
        for p in f.read_text(encoding="utf-8").splitlines():
            p = p.lower().replace("_", "-")
            if re.fullmatch(r"[a-z-]+", p):
                assert p + "==" in out_pkgs, f"Package `{p}` deleted from {out_file}"
        out_file.write_text(out_pkgs.replace(f"{ROOT}/", ""))


def update_python_versions():
    install.ensure_python(PYTHONS[ci_version])
    # `uv python list` prints one candidate per line; it reports only the
    # interpreters uv knows how to install, so we don't need to translate
    # from pyenv's naming scheme any more.
    result = subprocess.run(
        ["uv", "python", "list", "--all-versions", "--output-format", "text"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.decode()
    # Each line starts with something like `cpython-3.14.4-linux-aarch64-gnu`
    # or `cpython-3.14.4+freethreaded-linux-aarch64-gnu` or `pypy-3.10.16-…`.
    # We pull out the `(impl, version)` bit at the head.
    versions = []
    for line in result.splitlines():
        token = line.strip().split()[0] if line.strip() else ""
        if m := re.match(
            r"(cpython|pypy)-(\d+\.\d+\.\d+(?:[a-z]\d+)?)(\+freethreaded)?", token
        ):
            impl, ver, ft = m.groups()
            versions.append((impl, ver, bool(ft)))

    min_minor_version = int(
        re.search(
            r'requires-python = ">= ?3.(\d+)"',
            Path("hypothesis/pyproject.toml").read_text(encoding="utf-8"),
        ).group(1)
    )
    # For cpython we key by `3.NN` (or `3.NNt` for free-threaded) and pick the
    # newest available version. pypy we key by `pypyX.Y` and format as
    # `pypyX.Y-dev` → the existing PYTHONS dict keeps the upstream pypy
    # version string for informational purposes, so we reconstruct those.
    best = {}
    for impl, ver, ft in versions:
        major_minor = ".".join(ver.split(".")[:2])
        if int(major_minor.split(".")[-1]) < min_minor_version:
            continue
        if impl == "cpython":
            key = f"{major_minor}{'t' if ft else ''}"
            # see https://github.com/HypothesisWorks/hypothesis/pull/4772#issuecomment-4760983630
            if key == "3.13t":
                continue
            candidate = f"{ver}{'+freethreaded' if ft else ''}"
        else:
            assert impl == "pypy"
            key = f"pypy{major_minor}"
            # pypy3.10 is eol upstream, see https://github.com/HypothesisWorks/hypothesis/pull/4776
            if key == "pypy3.10":
                continue
            candidate = f"pypy{major_minor}-{ver}"
        # `uv python list` sorts newest-first, so first hit wins.
        best.setdefault(key, candidate)

    best = dict(sorted(best.items()))

    if best == PYTHONS:
        return

    # Write the new mapping back to this file
    thisfile = pathlib.Path(__file__)
    before = thisfile.read_text(encoding="utf-8")
    after = re.sub(r"\nPYTHONS = \{[^{}]+\}", f"\nPYTHONS = {best}", before)
    thisfile.write_text(after, encoding="utf-8")
    pip_tool("shed", str(thisfile))

    # Automatically sync ci_version with the version in build.sh
    build_sh = ROOT / "build.sh"
    sh_before = build_sh.read_text(encoding="utf-8")
    sh_after = re.sub(r"3\.\d\d?\.\d\d?", best[ci_version], sh_before)
    if sh_before != sh_after:
        build_sh.unlink()  # so bash doesn't reload a modified file
        build_sh.write_text(sh_after, encoding="utf-8")
        build_sh.chmod(0o755)


DJANGO_VERSIONS = {
    "5.2": "5.2.15",
    "6.0": "6.0.6",
}


def update_django_versions():
    # https://endoflife.date/django makes it easier to track these
    releases = requests.get("https://endoflife.date/api/django.json").json()
    versions = {r["cycle"]: r["latest"] for r in releases[::-1] if TODAY <= r["eol"]}

    if versions == DJANGO_VERSIONS:
        return

    # Write the new mapping back to this file
    thisfile = pathlib.Path(__file__)
    before = thisfile.read_text(encoding="utf-8")
    after = re.sub(
        r"DJANGO_VERSIONS = \{[^{}]+\}",
        "DJANGO_VERSIONS = " + repr(versions).replace("}", ",}"),
        before,
    )
    thisfile.write_text(after, encoding="utf-8")
    pip_tool("shed", str(thisfile))

    # Update the minimum version in pyproject.toml
    pyproject_toml = HYPOTHESIS / "pyproject.toml"
    content = re.sub(
        r"django>=\d+\.\d+",
        f"django>={min(versions, key=float)}",
        pyproject_toml.read_text(encoding="utf-8"),
    )
    pyproject_toml.write_text(content, encoding="utf-8")

    # Automatically sync ci_version with the version in build.sh
    tox_ini = HYPOTHESIS / "tox.ini"
    content = tox_ini.read_text(encoding="utf-8")
    print(versions)
    for short, full in versions.items():
        content = re.sub(
            rf"django=={short}(\.\d+)?",
            rf"django=={full}",
            content,
        )
    tox_ini.write_text(content, encoding="utf-8")


def update_pyodide_versions():

    def version_tuple(v: str) -> tuple[int, int, int]:
        return tuple(int(x) for x in v.split("."))  # type: ignore

    vers_re = r"(\d+\.\d+\.\d+)"
    all_pyodide_build_versions = re.findall(
        f"pyodide_build-{vers_re}-py3-none-any.whl",  # excludes pre-releases
        requests.get("https://pypi.org/simple/pyodide-build/").text,
    )
    pyodide_build_version = max(
        # Don't just pick the most recent version; find the highest stable version.
        set(all_pyodide_build_versions),
        key=version_tuple,
    )

    cross_build_environments_url = "https://raw.githubusercontent.com/pyodide/pyodide/refs/heads/main/metadata/pyodide-cross-build-environments-v2.json"
    cross_build_environments_data = requests.get(cross_build_environments_url).json()

    # Find the latest stable release for the Pyodide runtime/xbuildenv that is compatible
    # with the pyodide-build version we found
    stable_releases = [
        rel
        for rel in cross_build_environments_data["releases"].values()
        if re.fullmatch(vers_re, rel["version"])
    ]

    compatible_releases = []
    for rel in stable_releases:  # sufficiently large values
        min_build_version = rel.get("min_pyodide_build_version", "0.0.0")
        max_build_version = rel.get("max_pyodide_build_version", "999.999.999")

        # Perform version comparisons to avoid getting an incompatible pyodide-build version
        # with the Pyodide runtime
        if (
            version_tuple(min_build_version)
            <= version_tuple(pyodide_build_version)
            <= version_tuple(max_build_version)
        ):
            compatible_releases.append(rel)

    if not compatible_releases:
        raise RuntimeError(
            f"No compatible Pyodide release found for pyodide-build {pyodide_build_version}"
        )

    pyodide_release = max(
        compatible_releases,
        key=lambda rel: version_tuple(rel["version"]),
    )

    pyodide_version = pyodide_release["version"]
    python_version = pyodide_release["python_version"]

    ci_files = [
        ROOT / ".github/workflows/main.yml",
        ROOT / ".github/workflows/release.yml",
    ]
    for ci_file in ci_files:
        config = ci_file.read_text(encoding="utf-8")
        for name, var in [
            ("PYODIDE", pyodide_version),
            ("PYODIDE_BUILD", pyodide_build_version),
            ("PYTHON", python_version),
        ]:
            config = re.sub(
                f"{name}_VERSION: {vers_re}", f"{name}_VERSION: {var}", config
            )
        ci_file.write_text(config, encoding="utf-8")


def update_vendored_files():
    vendor = pathlib.Path(PYTHON_SRC) / "hypothesis" / "vendor"

    # Turns out that as well as adding new gTLDs, IANA can *terminate* old ones
    url = "http://data.iana.org/TLD/tlds-alpha-by-domain.txt"
    fname = vendor / url.split("/")[-1]
    new = requests.get(url).content
    # If only the timestamp in the header comment has changed, skip the update.
    if fname.read_bytes().splitlines()[1:] != new.splitlines()[1:]:
        fname.write_bytes(new)

    # Always require the most recent version of tzdata - we don't need to worry about
    # pre-releases because tzdata is a 'latest data' package  (unlike pyodide-build).
    # Our crosshair extra is research-grade, so we require latest versions there too.
    pyproject_toml = pathlib.Path(HYPOTHESIS, "pyproject.toml")
    new = pyproject_toml.read_text(encoding="utf-8")
    for pkgname in ("tzdata", "crosshair-tool", "hypothesis-crosshair"):
        pkg_url = f"https://pypi.org/pypi/{pkgname}/json"
        pkg_version = requests.get(pkg_url).json()["info"]["version"]
        new = re.sub(rf"{pkgname}>=([a-z0-9.]+)", f"{pkgname}>={pkg_version}", new)
    pyproject_toml.write_text(new, encoding="utf-8")


def has_diff(file_or_directory):
    diff = ["git", "diff", "--no-patch", "--exit-code", "--", file_or_directory]
    return subprocess.call(diff) != 0


@task()
def upgrade_requirements():
    update_vendored_files()
    compile_requirements(upgrade=True)
    # Reformat every file, not just changed ones: upgrading the formatters in
    # tools.txt can change how they format files we didn't otherwise touch, and
    # we want those changes in this PR rather than leaking into a later one.
    subprocess.call(
        ["./build.sh", "format"],
        cwd=ROOT,
        env={**os.environ, "FORMAT_ALL": "true"},
    )  # exits 1 if changed
    if has_diff(PYTHON_SRC) and not os.path.isfile(RELEASE_FILE):
        msg = get_autoupdate_message(domainlist_changed=has_diff(DOMAINS_LIST))
        with open(RELEASE_FILE, mode="w", encoding="utf-8") as f:
            f.write(f"RELEASE_TYPE: patch\n\n{msg}")
    update_python_versions()
    update_pyodide_versions()
    update_django_versions()
    subprocess.call(["git", "add", "."], cwd=ROOT)


@task()
def check_requirements():
    compile_requirements(upgrade=False)


@task(if_changed=HYPOTHESIS)
def documentation():
    try:
        if has_release():
            update_changelog_and_version()
        build_docs()
    finally:
        subprocess.check_call(
            ["git", "checkout", "docs/changelog.rst", "src/hypothesis/version.py"],
            cwd=HYPOTHESIS,
        )


@task()
def website():
    subprocess.call([sys.executable, "-m", "pelican"], cwd=ROOT / "website")


@task()
def live_website():
    subprocess.call(
        [sys.executable, "-m", "pelican", "--autoreload", "--listen"],
        cwd=ROOT / "website",
    )


@task()
def live_docs():
    pip_tool(
        "sphinx-autobuild",
        "docs",
        "docs/_build/html",
        "--watch",
        "src",
        "--open-browser",
        cwd=HYPOTHESIS,
    )


def run_tox(task, version, *args):
    python = install.python_executable(version)

    # Create a version of the name that tox will pick up for the correct
    # interpreter alias.
    linked_version = os.path.basename(python) + ALIASES[version]
    try:
        os.symlink(python, linked_version)
    except FileExistsError:
        pass

    env = dict(os.environ)
    python = install.python_executable(version)

    env["PATH"] = os.path.dirname(python) + ":" + env["PATH"]
    # Set environment variable for tox to use in basepython substitution
    if version.startswith("pypy"):
        # For PyPy, use the version name from e.g. "pypy3.11-7.3.20"
        # to match tox's environment name inference.
        env["TOX_PYTHON_VERSION"] = version.split("-")[0]  # "pypy3.11"
    else:
        env["TOX_PYTHON_VERSION"] = ALIASES[version]  # "python3.12"
    print(env["PATH"])

    pip_tool("tox", "-e", task, *args, env=env, cwd=HYPOTHESIS)


# update_python_versions(), above, keeps the contents of this dict up to date.
# When a version is added or removed, manually update the env lists in tox.ini and
# workflows/main.yml, and the `Programming Language ::` specifiers in pyproject.toml
PYTHONS = {
    "3.10": "3.10.20",
    "3.11": "3.11.15",
    "3.12": "3.12.13",
    "3.13": "3.13.14",
    "3.14": "3.14.6",
    "3.14t": "3.14.6+freethreaded",
    "3.15": "3.15.0b2",
    "3.15t": "3.15.0b2+freethreaded",
    "pypy3.11": "pypy3.11-3.11.15",
}
ci_version = "3.14"  # Keep this in sync with GH Actions main.yml and .readthedocs.yml

python_tests = task(
    if_changed=(
        PYTHON_SRC,
        PYTHON_TESTS,
        HYPOTHESIS / "rust",
        HYPOTHESIS / "pyproject.toml",
        ROOT / "tooling",
        HYPOTHESIS / "scripts",
    )
)


# ALIASES are the executable names for each Python version
ALIASES = {}
for key, version in PYTHONS.items():
    if key.startswith("pypy"):
        ALIASES[version] = "pypy3"
        name = key.replace(".", "")
    else:
        ALIASES[version] = f"python{key}"
        name = f"py3{key[2:]}"
    TASKS[f"check-{name}"] = python_tests(
        lambda n=f"{name}-full", v=version, *args: run_tox(n, v, *args)
    )
    for subtask in (
        "brief",
        "full",
        "cover",
        "rest",
        "nocover",
        "niche",
        "custom",
    ):
        TASKS[f"check-{name}-{subtask}"] = python_tests(
            lambda n=f"{name}-{subtask}", v=version, *args: run_tox(n, v, *args)
        )


@python_tests
def check_py310_pyjion(*args):
    run_tox("py310-pyjion", PYTHONS["3.10"], *args)


@task()
def tox(*args):
    if len(args) < 2:
        print("Usage: ./build.sh tox TOX_ENV PY_VERSION [tox args]")
        sys.exit(1)
    run_tox(*args)


def standard_tox_task(name, py=ci_version):
    TASKS["check-" + name] = python_tests(
        lambda *args: run_tox(name, PYTHONS.get(py, py), *args)
    )


standard_tox_task("py311-pytest62", py="3.11")  # hits "ast.Str is deprecated" in 3.12+
standard_tox_task("pytest74")
standard_tox_task("pytest84")
standard_tox_task("pytest9")

dj_version = max(ci_version, "3.12")
for n in DJANGO_VERSIONS:
    standard_tox_task(f"django{n.replace('.', '')}", py=dj_version)
# we also test no-contrib on the latest django version
standard_tox_task("django-nocontrib", py=dj_version)

# test each pandas version with the latest python version they support
standard_tox_task("py310-pandas11", py="3.10")
standard_tox_task("py310-pandas12", py="3.10")
standard_tox_task("py310-pandas13", py="3.10")
standard_tox_task("py310-pandas14", py="3.10")
standard_tox_task("py311-pandas15", py="3.11")
standard_tox_task("py311-pandas20", py="3.11")
standard_tox_task("py312-pandas21", py="3.12")
standard_tox_task("py313-pandas22", py="3.13")

for kind in ("cover", "nocover", "niche", "custom"):
    standard_tox_task(f"crosshair-{kind}")

for kind in ("rest", "nocover"):
    # Note, in CI these are executed on alternative platforms (e.g., windows)
    # directly in tox (and not via build.sh)
    standard_tox_task(f"alt-{kind}")

standard_tox_task("threading")
standard_tox_task("py310-oldestnumpy", py="3.10")
standard_tox_task("numpy-nightly", py="3.12")

standard_tox_task("coverage")
standard_tox_task("conjecture-coverage")
standard_tox_task("snapshots")


@task()
def check_quality(*args):
    run_tox("quality", PYTHONS[ci_version], *args)


@python_tests
def check_abi3(*args):
    with tempfile.TemporaryDirectory() as dist:
        pip_tool(
            "maturin", "build", "--features", "abi3", "--out", dist, cwd=HYPOTHESIS
        )
        (wheel,) = Path(dist).glob("*.whl")
        assert "abi3" in wheel.name, wheel.name
        slug = ci_version.replace(".", "")
        run_tox(f"py{slug}-cover", PYTHONS[ci_version], f"--installpkg={wheel}", *args)


@task()
def check_whole_repo_tests(*args):
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", HYPOTHESIS]
    )

    if not args:
        args = ["-n", "auto", REPO_TESTS / "whole_repo"]
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


@task()
def check_documentation(*args):
    install.ensure_shellcheck()
    # Here is why -e is necessary: our docs build prepends src/ onto sys.path so the local
    # source code is consulted first. Without -e, any rust code is compiled into site-packages,
    # which the src/ prepending will not reference. -e causes rust code to be compiled
    # into src/, which lets our sys.path edit pick it up.
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "-e", HYPOTHESIS]
    )

    if not args:
        args = ["-n", "auto", REPO_TESTS / "documentation"]
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


@task()
def check_types(*args):
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", HYPOTHESIS]
    )

    if not args:
        args = ["-n", "auto", REPO_TESTS / "types"]
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


@task()
def check_types_api(*args):
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", HYPOTHESIS]
    )

    if not args:
        ignore = ["--ignore", REPO_TESTS / "types/test_hypothesis.py"]
        args = ["-n", "auto", REPO_TESTS / "types"] + ignore
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


@task()
def check_types_hypothesis(*args):
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", HYPOTHESIS]
    )

    if not args:
        testcase = "types/test_hypothesis.py"
        args = ["-n", "auto", REPO_TESTS / testcase]
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


@task()
def shell():
    import IPython

    IPython.start_ipython([])


@task()
def python(*args):
    os.execv(sys.executable, (sys.executable, *args))


@task()
def tasks():
    """Print a list of all task names supported by the build system."""
    for task_name in sorted(TASKS.keys()):
        print("    " + task_name)


if __name__ == "__main__":
    if "SNAKEPIT" not in os.environ:
        print(
            "This module should not be executed directly, but instead via "
            "build.sh (which sets up its environment)"
        )
        sys.exit(1)

    if len(sys.argv) > 1:
        task_to_run = sys.argv[1]
        args = sys.argv[2:]
    else:
        task_to_run = os.environ.get("TASK")
        args = ()

    if task_to_run is None:
        print(
            "No task specified. Either pass the task to run as an "
            "argument or as an environment variable TASK. "
            '(Use "./build.sh tasks" to list all supported task names.)'
        )
        sys.exit(1)

    if task_to_run not in TASKS:
        print(f"\nUnknown task {task_to_run!r}.  Available tasks are:")
        tasks()
        sys.exit(1)

    try:
        TASKS[task_to_run](*args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
