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
from datetime import date
from pathlib import Path

import requests
from coverage.config import CoverageConfig

import hypothesistooling as tools
import hypothesistooling.projects.conjecturerust as cr
import hypothesistooling.projects.hypothesispython as hp
import hypothesistooling.projects.hypothesisruby as hr
from hypothesistooling import installers as install, releasemanagement as rm
from hypothesistooling.scripts import pip_tool

TASKS = {}
BUILD_FILES = tuple(
    os.path.join(tools.ROOT, f)
    for f in ["tooling", "requirements", ".github", "hypothesis-python/tox.ini"]
)
TODAY = date.today().isoformat()


def task(if_changed=()):
    if not isinstance(if_changed, tuple):
        if_changed = (if_changed,)

    def accept(fn):
        def wrapped(*args, **kwargs):
            if if_changed and tools.IS_PULL_REQUEST:
                if not tools.has_changes(if_changed + BUILD_FILES):
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
        "--ignore-words=./tooling/ignore-list.txt",
        "--skip=__pycache__,.mypy_cache,.venv,.git,tlds-alpha-by-domain.txt",
        *files,
    )


@task()
def lint():
    pip_tool("ruff", "check", ".")
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
    pip_tool("ruff", "check", "--fix-only", ".")
    pip_tool("shed", "--py39-plus", *files_to_format, *doc_files_to_format)


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
            "hypothesis-python/setup.py",
            "--output-file",
            str(out_file),
            cwd=tools.ROOT,
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
        out_file.write_text(out_pkgs.replace(f"{tools.ROOT}/", ""))


def update_python_versions():
    install.ensure_python(PYTHONS[ci_version])
    where = os.path.expanduser("~/.cache/hypothesis-build-runtimes/pyenv/")
    subprocess.run(
        "git fetch && git reset --hard origin/master",
        cwd=where,
        shell=True,
        capture_output=True,
    )
    cmd = "bin/pyenv install --list"
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, cwd=where
    ).stdout.decode()
    # pyenv reports available versions in chronological order, so we keep the newest
    # *unless* our current ends with a digit (is stable) and the candidate does not.
    # (plus some special cases for the `t` suffix for free-threading builds)
    stable = re.compile(r".*3\.\d+.\d+t?$")
    min_minor_version = re.search(
        r'python_requires=">= ?3.(\d+)"',
        Path("hypothesis-python/setup.py").read_text(encoding="utf-8"),
    ).group(1)
    best = {}
    for line in map(str.strip, result.splitlines()):
        if m := re.match(r"(?:pypy)?3\.(?:9|\d\dt?)", line):
            key = m.group()
            curr = best.get(key, line)
            if (
                (stable.match(line) or not stable.match(curr))
                and not (line.endswith("-dev") and not curr.endswith("-dev"))
                and int(key.split(".")[-1].rstrip("t")) >= int(min_minor_version)
                and key.endswith("t") == line.endswith(("t", "t-dev"))
            ):
                best[key] = line

    if best == PYTHONS:
        return

    # Write the new mapping back to this file
    thisfile = pathlib.Path(__file__)
    before = thisfile.read_text(encoding="utf-8")
    after = re.sub(r"\nPYTHONS = \{[^{}]+\}", f"\nPYTHONS = {best}", before)
    thisfile.write_text(after, encoding="utf-8")
    pip_tool("shed", str(thisfile))

    # Automatically sync ci_version with the version in build.sh
    build_sh = tools.ROOT / "build.sh"
    sh_before = build_sh.read_text(encoding="utf-8")
    sh_after = re.sub(r"3\.\d\d?\.\d\d?", best[ci_version], sh_before)
    if sh_before != sh_after:
        build_sh.unlink()  # so bash doesn't reload a modified file
        build_sh.write_text(sh_after, encoding="utf-8")
        build_sh.chmod(0o755)


DJANGO_VERSIONS = {
    "4.2": "4.2.18",
    "5.0": "5.0.11",
    "5.1": "5.1.5",
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

    # Update the minimum version in setup.py
    setup_py = hp.BASE_DIR / "setup.py"
    content = re.sub(
        r"django>=\d+\.\d+",
        f"django>={min(versions, key=float)}",
        setup_py.read_text(encoding="utf-8"),
    )
    setup_py.write_text(content, encoding="utf-8")

    # Automatically sync ci_version with the version in build.sh
    tox_ini = hp.BASE_DIR / "tox.ini"
    content = tox_ini.read_text(encoding="utf-8")
    print(versions)
    for short, full in versions.items():
        content = re.sub(
            rf"(pip install django==){short}\.\d+",
            rf"\g<1>{full}",
            content,
        )
    tox_ini.write_text(content, encoding="utf-8")


def update_pyodide_versions():
    vers_re = r"(\d+\.\d+\.\d+)"
    all_versions = re.findall(
        f"pyodide_build-{vers_re}-py3-none-any.whl",  # excludes pre-releases
        requests.get("https://pypi.org/simple/pyodide-build/").text,
    )
    for pyodide_version in sorted(
        # Don't just pick the most recent version; find the highest stable version.
        set(all_versions),
        key=lambda version: tuple(int(x) for x in version.split(".")),
        reverse=True,
    ):
        makefile_url = f"https://raw.githubusercontent.com/pyodide/pyodide/{pyodide_version}/Makefile.envs"
        match = re.search(
            rf"export PYVERSION \?= {vers_re}\nexport PYODIDE_EMSCRIPTEN_VERSION \?= {vers_re}\n",
            requests.get(makefile_url).text,
        )
        if match is not None:
            python_version, emscripten_version = match.groups()
            break
    ci_file = tools.ROOT / ".github/workflows/main.yml"
    config = ci_file.read_text(encoding="utf-8")
    for name, var in [
        ("PYODIDE", pyodide_version),
        ("PYTHON", python_version),
        ("EMSCRIPTEN", emscripten_version),
    ]:
        config = re.sub(f"{name}_VERSION: {vers_re}", f"{name}_VERSION: {var}", config)
    ci_file.write_text(config, encoding="utf-8")


def update_vendored_files():
    vendor = pathlib.Path(hp.PYTHON_SRC) / "hypothesis" / "vendor"

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
    setup = pathlib.Path(hp.BASE_DIR, "setup.py")
    new = setup.read_text(encoding="utf-8")
    for pkgname in ("tzdata", "crosshair-tool", "hypothesis-crosshair"):
        pkg_url = f"https://pypi.org/pypi/{pkgname}/json"
        pkg_version = requests.get(pkg_url).json()["info"]["version"]
        new = re.sub(rf"{pkgname}>=([a-z0-9.]+)", f"{pkgname}>={pkg_version}", new)
    setup.write_text(new, encoding="utf-8")


def has_diff(file_or_directory):
    diff = ["git", "diff", "--no-patch", "--exit-code", "--", file_or_directory]
    return subprocess.call(diff) != 0


@task()
def upgrade_requirements():
    update_vendored_files()
    compile_requirements(upgrade=True)
    subprocess.call(["./build.sh", "format"], cwd=tools.ROOT)  # exits 1 if changed
    if has_diff(hp.PYTHON_SRC) and not os.path.isfile(hp.RELEASE_FILE):
        msg = hp.get_autoupdate_message(domainlist_changed=has_diff(hp.DOMAINS_LIST))
        with open(hp.RELEASE_FILE, mode="w", encoding="utf-8") as f:
            f.write(f"RELEASE_TYPE: patch\n\n{msg}")
    update_python_versions()
    update_pyodide_versions()
    update_django_versions()
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


@task()
def website():
    subprocess.call(["pelican"], cwd=tools.ROOT / "website")


@task()
def live_website():
    subprocess.call(["pelican", "--autoreload", "--listen"], cwd=tools.ROOT / "website")


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
    print(env["PATH"])

    pip_tool("tox", "-e", task, *args, env=env, cwd=hp.HYPOTHESIS_PYTHON)


# update_python_versions(), above, keeps the contents of this dict up to date.
# When a version is added or removed, manually update the env lists in tox.ini and
# workflows/main.yml, and the `Programming Language ::` specifiers in setup.py
PYTHONS = {
    "3.9": "3.9.21",
    "3.10": "3.10.16",
    "3.11": "3.11.11",
    "3.12": "3.12.8",
    "3.13": "3.13.1",
    "3.13t": "3.13t-dev",
    "3.14": "3.14.0a4",
    "3.14t": "3.14t-dev",
    "pypy3.9": "pypy3.9-7.3.16",
    "pypy3.10": "pypy3.10-7.3.17",
}
ci_version = "3.10"  # Keep this in sync with GH Actions main.yml and .readthedocs.yml

python_tests = task(
    if_changed=(
        hp.PYTHON_SRC,
        hp.PYTHON_TESTS,
        os.path.join(tools.ROOT, "pytest.ini"),
        os.path.join(tools.ROOT, "tooling"),
        os.path.join(hp.HYPOTHESIS_PYTHON, "scripts"),
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
    for subtask in ("brief", "full", "cover", "nocover", "niche", "custom"):
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


standard_tox_task("py39-nose", py="3.9")
standard_tox_task("py39-pytest46", py="3.9")
standard_tox_task("py39-pytest54", py="3.9")
standard_tox_task("pytest62")

for n in DJANGO_VERSIONS:
    standard_tox_task(f"django{n.replace('.', '')}")

for n in [13, 14, 15, 20, 21, 22]:
    standard_tox_task(f"pandas{n}")
standard_tox_task("py39-pandas11", py="3.9")
standard_tox_task("py39-pandas12", py="3.9")

for kind in ("cover", "nocover", "niche", "custom"):
    standard_tox_task(f"crosshair-{kind}")

standard_tox_task("py39-oldestnumpy", py="3.9")
standard_tox_task("numpy-nightly", py="3.12")

standard_tox_task("coverage")
standard_tox_task("conjecture-coverage")


@task()
def check_quality(*args):
    run_tox("quality", PYTHONS[ci_version], *args)


@task(if_changed=(hp.PYTHON_SRC, os.path.join(hp.HYPOTHESIS_PYTHON, "examples")))
def check_examples3(*args):
    run_tox("examples3", PYTHONS[ci_version], *args)


@task()
def check_whole_repo_tests(*args):
    install.ensure_shellcheck()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", hp.HYPOTHESIS_PYTHON]
    )

    if not args:
        args = ["-n", "auto", tools.REPO_TESTS]
    subprocess.check_call([sys.executable, "-m", "pytest", *args])


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
    os.execv(sys.executable, (sys.executable, *args))


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
