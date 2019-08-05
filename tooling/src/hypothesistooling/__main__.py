# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import os
import shlex
import subprocess
import sys
from datetime import datetime
from glob import glob

import hypothesistooling as tools
import hypothesistooling.installers as install
import hypothesistooling.projects.conjecturerust as cr
import hypothesistooling.projects.hypothesispython as hp
import hypothesistooling.projects.hypothesisruby as hr
import hypothesistooling.releasemanagement as rm
from hypothesistooling.scripts import pip_tool

TASKS = {}
BUILD_FILES = tuple(
    os.path.join(tools.ROOT, f)
    for f in ["tooling", "requirements", ".travis.yml", "hypothesis-python/tox.ini"]
)


def task(if_changed=()):
    if isinstance(if_changed, str):
        if_changed = (if_changed,)

    def accept(fn):
        def wrapped(*args, **kwargs):
            if if_changed and tools.IS_PULL_REQUEST:
                if not tools.has_changes(if_changed + BUILD_FILES):
                    print(
                        "Skipping task due to no changes in %s"
                        % (", ".join(if_changed),)
                    )
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


@task()
def lint():
    pip_tool(
        "flake8",
        *[f for f in tools.all_files() if f.endswith(".py")],
        "--config",
        os.path.join(tools.ROOT, ".flake8"),
    )
    # Check for redefined test functions, where e.g. a copy-pasted definition
    # will shadow the earlier test and Pytest never sees or executes it.
    pip_tool(
        "pylint",
        "--score=n",
        "--jobs=0",
        "--disable=all",
        "--enable=function-redefined",
        "hypothesis-python/tests/",
    )


HEAD = tools.hash_for_name("HEAD")
MASTER = tools.hash_for_name("origin/master")


def do_release(package):
    if not package.has_release():
        print("No release for %s" % (package.__name__,))
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

    print("Creating tag %s" % (tag_name,))

    tools.create_tag(tag_name)
    tools.push_tag(tag_name)

    print("Uploading distribution")
    package.upload_distribution()


@task()
def deploy():
    print("Current head:  ", HEAD)
    print("Current master:", MASTER)

    if not tools.is_ancestor(HEAD, MASTER):
        print("Not deploying due to not being on master")
        sys.exit(0)

    if not tools.has_travis_secrets():
        print("Running without access to secure variables, so no deployment")
        sys.exit(0)

    print("Decrypting secrets")
    tools.decrypt_secrets()
    tools.configure_git()

    for project in tools.all_projects():
        do_release(project)

    sys.exit(0)


CURRENT_YEAR = datetime.utcnow().year


HEADER = """
# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-%(year)s David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER""".strip() % {
    "year": CURRENT_YEAR
}


@task()
def format():
    def should_format_file(path):
        if "vendor" in path.split(os.path.sep):
            return False
        return path.endswith(".py")

    changed = tools.modified_files()

    format_all = os.environ.get("FORMAT_ALL", "").lower() == "true"
    if "requirements/tools.txt" in changed:
        # We've changed the tools, which includes a lot of our formatting
        # logic, so we need to rerun formatters.
        format_all = True

    files = tools.all_files() if format_all else changed

    files_to_format = [f for f in sorted(files) if should_format_file(f)]

    if not files_to_format:
        return

    for f in files_to_format:
        lines = []
        with open(f, encoding="utf-8") as o:
            shebang = None
            first = True
            header_done = False
            for l in o.readlines():
                if first:
                    first = False
                    if l[:2] == "#!":
                        shebang = l
                        continue
                if "END HEADER" in l and not header_done:
                    lines = []
                    header_done = True
                else:
                    lines.append(l)
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

    pip_tool(
        "autoflake",
        "--recursive",
        "--in-place",
        "--exclude=compat.py",
        "--remove-all-unused-imports",
        "--remove-duplicate-keys",
        "--remove-unused-variables",
        *files_to_format,
    )
    pip_tool("pyupgrade", "--keep-percent-format", *files_to_format)
    pip_tool("isort", *files_to_format)
    pip_tool("black", *files_to_format)


VALID_STARTS = ("# coding=utf-8", "#!/usr/bin/env python")


@task()
def check_format():
    format()
    n = max(map(len, VALID_STARTS))
    bad = False
    for f in tools.all_files():
        if not f.endswith(".py"):
            continue
        with open(f, "r", encoding="utf-8") as i:
            start = i.read(n)
            if not any(start.startswith(s) for s in VALID_STARTS):
                print("%s has incorrect start %r" % (f, start), file=sys.stderr)
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
            "pip-compile", *extra, f, "--output-file", base + ".txt", cwd=tools.ROOT
        )


@task()
def upgrade_requirements():
    compile_requirements(upgrade=True)


def is_pyup_branch():
    if os.environ.get("TRAVIS_EVENT_TYPE") == "pull_request" and os.environ.get(
        "TRAVIS_PULL_REQUEST_BRANCH", ""
    ).startswith("pyup-scheduled-update"):
        return True
    return (
        os.environ.get("Build.SourceBranchName", "").startswith("pyup-scheduled-update")
        and os.environ.get("System.PullRequest.IsFork") == "False"
        and os.environ.get("Build.Reason") == "PullRequest"
    )


def push_pyup_requirements_commit():
    """Because pyup updates each package individually, it can create a
    requirements.txt with an incompatible set of versions.

    Depending on the changes, pyup might also have introduced
    whitespace errors.

    If we've recompiled requirements.txt in Travis and made changes,
    and this is a PR where pyup is running, push a consistent set of
    versions as a new commit to the PR.
    """
    if is_pyup_branch():
        print("Pushing new requirements, as this is a pyup pull request")

        print("Decrypting secrets")
        tools.decrypt_secrets()
        tools.configure_git()

        print("Creating commit")
        tools.git("add", "--update", "requirements")
        tools.git("commit", "-m", "Bump requirements for pyup pull request")

        print("Pushing to GitHub")
        subprocess.check_call(
            [
                "ssh-agent",
                "sh",
                "-c",
                "ssh-add %s && " % (shlex.quote(tools.DEPLOY_KEY),)
                + "git push ssh-origin HEAD:%s"
                % (os.environ["TRAVIS_PULL_REQUEST_BRANCH"],),
            ]
        )


@task()
def check_requirements():
    if is_pyup_branch() and tools.last_committer() != tools.TOOLING_COMMITER_NAME:
        # Recompile to fix broken formatting etc., but ensure there can't be a loop.
        compile_requirements(upgrade=True)
        if tools.has_uncommitted_changes("requirements"):
            push_pyup_requirements_commit()
            raise RuntimeError("Pushed new requirements; check next build.")
    else:
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


PY27 = "2.7.14"
PY35 = "3.5.5"
PY36 = "3.6.8"
PY37 = "3.7.0"
PYPY2 = "pypy2.7-5.10.0"
PYPY3 = "pypy3.5-5.10.1"


@task()
def install_core():
    install.python_executable(PY27)
    install.python_executable(PY36)


ALIASES = {PYPY2: "pypy", PYPY3: "pypy3"}

for n in [PY27, PY35, PY36, PY37]:
    major, minor, patch = n.split(".")
    ALIASES[n] = "python%s.%s" % (major, minor)


python_tests = task(
    if_changed=(
        hp.PYTHON_SRC,
        hp.PYTHON_TESTS,
        os.path.join(hp.HYPOTHESIS_PYTHON, "scripts"),
    )
)


@python_tests
def check_py27():
    run_tox("py27-full", PY27)


@python_tests
def check_py35():
    run_tox("py35-full", PY35)


@python_tests
def check_py36():
    run_tox("py36-full", PY36)


@python_tests
def check_py37():
    run_tox("py37-full", PY37)


@python_tests
def check_pypy():
    run_tox("pypy-full", PYPY2)


@python_tests
def check_pypy3():
    run_tox("pypy3-full", PYPY3)


@python_tests
def check_py27_typing():
    run_tox("py27typing", PY27)


@python_tests
def check_pypy_with_tracer():
    run_tox("pypy-with-tracer", PYPY2)


def standard_tox_task(name):
    TASKS["check-" + name] = python_tests(lambda: run_tox(name, PY36))


standard_tox_task("nose")
standard_tox_task("pytest30")

for n in [20, 21, 22, 111]:
    standard_tox_task("django%d" % (n,))
for n in [19, 20, 21, 22, 23, 24, 25]:
    standard_tox_task("pandas%d" % (n,))

standard_tox_task("coverage")


@task()
def check_quality():
    run_tox("quality", PY36)


examples_task = task(
    if_changed=(hp.PYTHON_SRC, os.path.join(hp.HYPOTHESIS_PYTHON, "examples"))
)


@examples_task
def check_examples2():
    run_tox("examples2", PY27)


@examples_task
def check_examples3():
    run_tox("examples3", PY36)


@python_tests
def check_unicode():
    run_tox("unicode", PY27)


@task()
def check_whole_repo_tests():
    install.ensure_shellcheck()
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
    hr.rake_task("test")


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
            "argument or as an environment variable TASK."
        )
        sys.exit(1)

    try:
        TASKS[task_to_run](*args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
