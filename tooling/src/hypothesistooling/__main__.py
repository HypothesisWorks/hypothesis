# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import pathlib
import re
import subprocess
import sys
from glob import glob
from urllib.parse import urlparse

import hypothesistooling as tools
import hypothesistooling.projects.conjecturerust as cr
import hypothesistooling.projects.hypothesispython as hp
import hypothesistooling.projects.hypothesisruby as hr
import requests
from coverage.config import CoverageConfig
from hypothesistooling import installers as install, releasemanagement as rm
from hypothesistooling.scripts import pip_tool

TASKS = {}
BUILD_FILES = tuple(
    os.path.join(tools.ROOT, f)
    for f in ["tooling", "requirements", ".github", "hypothesis-python/tox.ini"]
)


def task(if_changed=()):
    if isinstance(if_changed, str):
        if_changed = (if_changed,)

    def accept(fn):
        def wrapped(*args, **kwargs):
            if if_changed and tools.IS_PULL_REQUEST:
                if not tools.has_changes(if_changed + BUILD_FILES):
                    changed = ", ".join(if_changed)
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
        "--ignore-words=./tooling/ignore-list.txt",
        "--skip=__pycache__,.mypy_cache,.venv,.git,tlds-alpha-by-domain.txt",
        *files,
    )


@task()
def lint():
    pip_tool(
        "flake8",
        *(f for f in tools.all_files() if f.endswith(".py")),
        "--config",
        os.path.join(tools.ROOT, ".flake8"),
    )
    codespell(*(f for f in tools.all_files() if not f.endswith("by-domain.txt")))


def do_release(package):
    if not package.has_release():
        print(f"No release for {package.__name__}")
        return

    os.chdir(package.BASE_DIR)

    print("Updating changelog and version")
    package.update_changelog_and_version()

    print("Committing changes")
    rm.commit_pending_release(package)

    print("Building distribution")
    package.build_distribution()

    print("Looks good to release!")

    tag_name = package.tag_name()

    print(f"Creating tag {tag_name}")

    tools.create_tag(tag_name)
    tools.push_tag(tag_name)

    print("Uploading distribution")
    package.upload_distribution()


@task()
def deploy():
    HEAD = tools.hash_for_name("HEAD")
    MASTER = tools.hash_for_name("origin/master")

    print("Current head:  ", HEAD)
    print("Current master:", MASTER)

    if not tools.is_ancestor(HEAD, MASTER):
        print("Not deploying due to not being on master")
        sys.exit(0)

    if "TWINE_PASSWORD" not in os.environ:
        print("Running without access to secure variables, so no deployment")
        sys.exit(0)

    tools.configure_git()

    for project in tools.all_projects():
        do_release(project)

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


@task()
def format():
    def should_format_file(path):
        return path.endswith(".py")

    def should_format_doc_file(path):
        return path.endswith((".rst", ".md"))

    changed = tools.modified_files()

    format_all = os.environ.get("FORMAT_ALL", "").lower() == "true"
    if "requirements/tools.txt" in changed:
        # We've changed the tools, which includes a lot of our formatting
        # logic, so we need to rerun formatters.
        format_all = True

    files = tools.all_files() if format_all else changed

    doc_files_to_format = [f for f in sorted(files) if should_format_doc_file(f)]
    files_to_format = [f for f in sorted(files) if should_format_file(f)]

    if not (files_to_format or doc_files_to_format):
        return

    # .coveragerc lists several regex patterns to treat as nocover pragmas, and
    # we want to find (and delete) cases where # pragma: no cover is redundant.
    def warn(msg):
        raise Exception(msg)

    config = CoverageConfig()
    config.from_file(os.path.join(hp.BASE_DIR, ".coveragerc"), warn=warn, our_file=True)
    pattern = "|".join(l for l in config.exclude_list if "pragma" not in l)
    unused_pragma_pattern = re.compile(f"(({pattern}).*)  # pragma: no (branch|cover)")
    last_header_line = HEADER.splitlines()[-1].rstrip()

    for f in files_to_format:
        lines = []
        with open(f, encoding="utf-8") as o:
            shebang = None
            first = True
            in_header = True
            for l in o.readlines():
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
        with open(f, "w", encoding="utf-8") as o:
            if shebang is not None:
                o.write(shebang)
                o.write("\n")
            o.write(HEADER)
            if source:
                o.write("\n\n")
                o.write(source)
            o.write("\n")

    codespell("--write-changes", *files_to_format, *doc_files_to_format)
    pip_tool("shed", *files_to_format, *doc_files_to_format)


VALID_STARTS = (HEADER.split()[0], "#!/usr/bin/env python")


@task()
def check_format():
    format()
    n = max(map(len, VALID_STARTS))
    bad = False
    for f in tools.all_files():
        if not f.endswith(".py"):
            continue
        with open(f, encoding="utf-8") as i:
            start = i.read(n)
            if not any(start.startswith(s) for s in VALID_STARTS):
                print(f"{f} has incorrect start {start!r}", file=sys.stderr)
                bad = True
    assert not bad
    check_not_changed()


def check_not_changed():
    subprocess.check_call(["git", "diff", "--exit-code"])


@task()
def compile_requirements(upgrade=False):
    if upgrade:
        extra = ["--upgrade"]
    else:
        extra = []

    for f in glob(os.path.join("requirements", "*.in")):
        base, _ = os.path.splitext(f)
        pip_tool(
            "pip-compile",
            *extra,
            f,
            "hypothesis-python/setup.py",
            "--output-file",
            base + ".txt",
            cwd=tools.ROOT,
        )


def update_python_versions():
    install.ensure_python(PYMAIN)  # ensures pyenv is installed and up to date
    cmd = "~/.cache/hypothesis-build-runtimes/pyenv/bin/pyenv install --list"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode()
    # pyenv reports available versions in chronological order, so we keep the newest
    # *unless* our current ends with a digit (is stable) and the candidate does not.
    stable = re.compile(r".*3\.\d+.\d+$")
    best = {}
    for line in map(str.strip, result.splitlines()):
        if m := re.match(r"(?:pypy)?3\.(?:[6-9]|\d\d)", line):
            key = m.group()
            if stable.match(line) or not stable.match(best.get(key, line)):
                best[key] = line
    print(best)
    thisfile = pathlib.Path(__file__)
    before = after = thisfile.read_text()
    for key, version in best.items():
        var = key.upper().replace(".", "")
        after = re.sub(rf'({var} = .*?"){key}[^"]+', rf"\g<1>{version}", after)
    if before != after:
        thisfile.write_text(after)

    # Automatically sync PYMAIN with the version in build.sh
    build_sh = pathlib.Path(tools.ROOT) / "build.sh"
    sh_before = build_sh.read_text()
    new_pymain = re.search(r'PYMAIN = "(3\.\d\d?\.\d\d?)"', after).group(1)
    sh_after = re.sub(r"3\.\d\d?\.\d\d?", new_pymain, sh_before)
    if sh_before != sh_after:
        build_sh.unlink()  # so bash doesn't reload a modified file
        build_sh.write_text(sh_after)
        build_sh.chmod(0o755)


def update_vendored_files():
    vendor = pathlib.Path(hp.PYTHON_SRC) / "hypothesis" / "vendor"

    # Turns out that as well as adding new gTLDs, IANA can *terminate* old ones
    url = "http://data.iana.org/TLD/tlds-alpha-by-domain.txt"
    fname = vendor / urlparse(url).path.split("/")[-1]
    new = requests.get(url).content
    # If only the timestamp in the header comment has changed, skip the update.
    if fname.read_bytes().splitlines()[1:] != new.splitlines()[1:]:
        fname.write_bytes(new)

    # Always require the latest version of the tzdata package
    tz_url = "https://pypi.org/pypi/tzdata/json"
    tzdata_version = requests.get(tz_url).json()["info"]["version"]
    setup = pathlib.Path(hp.BASE_DIR, "setup.py")
    new = re.sub(r"tzdata>=(.+?) ", f"tzdata>={tzdata_version} ", setup.read_text())
    setup.write_text(new)


def has_diff(file_or_directory):
    diff = ["git", "diff", "--no-patch", "--exit-code", "--", file_or_directory]
    return subprocess.call(diff) != 0


@task()
def upgrade_requirements():
    update_vendored_files()
    compile_requirements(upgrade=True)
    subprocess.call(["./build.sh", "format"], cwd=tools.ROOT)  # exits 1 if changed
    if has_diff(hp.PYTHON_SRC) and not os.path.isfile(hp.RELEASE_FILE):
        if has_diff(f"{hp.PYTHON_SRC}/hypothesis/vendor/tlds-alpha-by-domain.txt"):
            msg = (
                "our vendored `list of top-level domains "
                "<https://www.iana.org/domains/root/db>`__,\nwhich is used by the "
                "provisional :func:`~hypothesis.provisional.domains` strategy."
            )
        else:
            msg = "our autoformatting tools, improving our code style without any API changes."
        with open(hp.RELEASE_FILE, mode="w") as f:
            f.write(f"RELEASE_TYPE: patch\n\nThis patch updates {msg}\n")
    update_python_versions()
    subprocess.call(["git", "add", "."], cwd=tools.ROOT)


@task()
def check_requirements():
    compile_requirements(upgrade=False)


@task(if_changed=hp.HYPOTHESIS_PYTHON)
def documentation():
    try:
        if hp.has_release():
            hp.update_changelog_and_version()
        hp.build_docs()
    finally:
        subprocess.check_call(
            ["git", "checkout", "docs/changes.rst", "src/hypothesis/version.py"],
            cwd=hp.HYPOTHESIS_PYTHON,
        )


def run_tox(task, version):
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
    print(env["PATH"])

    pip_tool("tox", "-e", task, env=env, cwd=hp.HYPOTHESIS_PYTHON)


# See update_python_versions() above
# When adding or removing a version, also update the env lists in tox.ini and
# workflows/main.yml, the `Programming Language ::` declaration(s) in setup.py,
# and the corresponding @python_tests function below.
PY37 = "3.7.12"
PY38 = PYMAIN = "3.8.12"  # Sync PYMAIN minor version with GH Actions main.yml
PY39 = "3.9.10"
PY310 = "3.10.2"
PY311 = "3.11-dev"
PYPY37 = "pypy3.7-7.3.7"
PYPY38 = "pypy3.8-7.3.7"


# ALIASES are the executable names for each Python version
ALIASES = {}
for name, value in list(globals().items()):
    if name.startswith("PYPY"):
        ALIASES[value] = "pypy3"
    elif name.startswith("PY"):
        major, minor, patch = value.replace("-dev", ".").split(".")
        ALIASES[value] = f"python{major}.{minor}"


python_tests = task(
    if_changed=(
        hp.PYTHON_SRC,
        hp.PYTHON_TESTS,
        os.path.join(tools.ROOT, "pytest.ini"),
        os.path.join(hp.HYPOTHESIS_PYTHON, "scripts"),
    )
)


@python_tests
def check_py37():
    run_tox("py37-full", PY37)


@python_tests
def check_py38():
    run_tox("py38-full", PY38)


@python_tests
def check_py39():
    run_tox("py39-full", PY39)


@python_tests
def check_py310():
    run_tox("py310-full", PY310)


@python_tests
def check_py311():
    run_tox("py311-full", PY311)


@python_tests
def check_py310_pyjion():
    run_tox("py310-pyjion", PY310)


@python_tests
def check_pypy37():
    run_tox("pypy3-full", PYPY37)


@python_tests
def check_pypy38():
    run_tox("pypy3-full", PYPY38)


def standard_tox_task(name):
    TASKS["check-" + name] = python_tests(lambda: run_tox(name, PYMAIN))


standard_tox_task("nose")
standard_tox_task("pytest46")

for n in [22, 32, 40]:
    standard_tox_task(f"django{n}")
for n in [25, 10, 11, 12, 13]:
    standard_tox_task(f"pandas{n}")

standard_tox_task("coverage")
standard_tox_task("conjecture-coverage")


@task()
def check_quality():
    run_tox("quality", PYMAIN)


@task(if_changed=(hp.PYTHON_SRC, os.path.join(hp.HYPOTHESIS_PYTHON, "examples")))
def check_examples3():
    run_tox("examples3", PYMAIN)


@task()
def check_whole_repo_tests():
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", hp.HYPOTHESIS_PYTHON]
    )
    subprocess.check_call([sys.executable, "-m", "pytest", tools.REPO_TESTS])


@task()
def shell():
    import IPython

    IPython.start_ipython([])


def ruby_task(fn):
    return task(if_changed=(hr.HYPOTHESIS_RUBY,))(fn)


@ruby_task
def lint_ruby():
    hr.rake_task("checkformat")


@ruby_task
def check_ruby_tests():
    hr.rake_task("rspec")
    hr.rake_task("minitest")


@ruby_task
def format_rust_in_ruby():
    hr.cargo("fmt")


@ruby_task
def check_rust_in_ruby_format():
    hr.cargo("fmt", "--", "--check")


@ruby_task
def lint_rust_in_ruby():
    hr.cargo("clippy")


@ruby_task
def audit_rust_in_ruby():
    hr.cargo("install", "cargo-audit")
    hr.cargo("audit")


@task()
def python(*args):
    os.execv(sys.executable, (sys.executable,) + args)


@task()
def bundle(*args):
    hr.bundle(*args)


rust_task = task(if_changed=(cr.BASE_DIR,))


@rust_task
def check_rust_tests():
    cr.cargo("test")


@rust_task
def format_conjecture_rust_code():
    cr.cargo("fmt")


@rust_task
def check_conjecture_rust_format():
    cr.cargo("fmt", "--", "--check")


@rust_task
def lint_conjecture_rust():
    cr.cargo("clippy")


@rust_task
def audit_conjecture_rust():
    cr.cargo("install", "cargo-audit")
    cr.cargo("audit")


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
