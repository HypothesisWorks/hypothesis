# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import sys
import subprocess
from glob import glob
from datetime import datetime

import hypothesistooling as tools
import hypothesistooling.installers as install
import hypothesistooling.releasemanagement as rm
import hypothesistooling.projects.hypothesisruby as hr
import hypothesistooling.projects.hypothesispython as hp
from hypothesistooling import fix_doctests as fd
from hypothesistooling.scripts import pip_tool

TASKS = {}
BUILD_FILES = tuple(os.path.join(tools.ROOT, f) for f in [
    'tooling', '.travis.yml',
])


def task(if_changed=()):
    if isinstance(if_changed, str):
        if_changed = (if_changed,)

    def accept(fn):
        def wrapped(*args):
            if if_changed and tools.IS_PULL_REQUEST:
                if not tools.has_changes(if_changed + BUILD_FILES):
                    print('Skipping task due to no changes in %s' % (
                        ', '.join(if_changed),
                    ))
                    return
            fn(*args)
        wrapped.__name__ = fn.__name__

        name = fn.__name__.replace('_', '-')
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
        'flake8',
        *[f for f in tools.all_files() if f.endswith('.py')],
        '--config', os.path.join(tools.ROOT, '.flake8'),
    )


@task(if_changed=hp.PYTHON_SRC)
def check_type_hints():
    pip_tool('mypy', hp.PYTHON_SRC)


HEAD = tools.hash_for_name('HEAD')
MASTER = tools.hash_for_name('origin/master')


def do_release(package):
    if not package.has_release():
        print('No release for %s' % (package.__name__,))
        return

    os.chdir(package.BASE_DIR)

    print('Updating changelog and version')
    package.update_changelog_and_version()

    print('Committing changes')
    rm.commit_pending_release(package)

    print('Building distribution')
    package.build_distribution()

    print('Looks good to release!')

    tag_name = package.tag_name()

    print('Creating tag %s' % (tag_name,))

    tools.create_tag(tag_name)

    print('Uploading distribution')
    package.upload_distribution()

    print('Pushing tag')
    tools.push_tag(tag_name)


@task()
def deploy():
    print('Current head:  ', HEAD)
    print('Current master:', MASTER)

    if not tools.is_ancestor(HEAD, MASTER):
        print('Not deploying due to not being on master')
        sys.exit(0)

    if not tools.has_travis_secrets():
        print('Running without access to secure variables, so no deployment')
        sys.exit(0)

    print('Decrypting secrets')
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
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-%(year)s David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER""".strip() % {
    'year': CURRENT_YEAR,
}


@task()
def format():
    def should_format_file(path):
        if os.path.basename(path) in (
            'header.py', 'test_lambda_formatting.py'
        ):
            return False
        if 'vendor' in path.split(os.path.sep):
            return False
        return path.endswith('.py')

    changed = tools.modified_files()

    format_all = os.environ.get('FORMAT_ALL', '').lower() == 'true'
    if 'scripts/header.py' in changed:
        # We've changed the header, so everything needs its header updated.
        format_all = True
    if 'requirements/tools.txt' in changed:
        # We've changed the tools, which includes a lot of our formatting
        # logic, so we need to rerun formatters.
        format_all = True

    files = tools.all_files() if format_all else changed

    files_to_format = [f for f in sorted(files) if should_format_file(f)]

    if not files_to_format:
        return

    for f in files_to_format:
        print(f)
        lines = []
        with open(f, encoding='utf-8') as o:
            shebang = None
            first = True
            header_done = False
            for l in o.readlines():
                if first:
                    first = False
                    if l[:2] == '#!':
                        shebang = l
                        continue
                if 'END HEADER' in l and not header_done:
                    lines = []
                    header_done = True
                else:
                    lines.append(l)
        source = ''.join(lines).strip()
        with open(f, 'w', encoding='utf-8') as o:
            if shebang is not None:
                o.write(shebang)
                o.write('\n')
            o.write(HEADER)
            if source:
                o.write('\n\n')
                o.write(source)
            o.write('\n')
    pip_tool(
        'isort', '-p', 'hypothesis', '-ls', '-m', '2', '-w', '75', '-a',
        'from __future__ import absolute_import, print_function, division',
        *files_to_format,
    )

    pip_tool('pyformat', '-i', *files_to_format)


VALID_STARTS = (
    '# coding=utf-8',
    '#!/usr/bin/env python',
)


@task()
def check_format():
    format()
    n = max(map(len, VALID_STARTS))
    bad = False
    for f in tools.all_files():
        if not f.endswith('.py'):
            continue
        with open(f, 'r', encoding='utf-8') as i:
            start = i.read(n)
            if not any(start.startswith(s) for s in VALID_STARTS):
                print(
                    '%s has incorrect start %r' % (f, start), file=sys.stderr)
                bad = True
    if bad:
        sys.exit(1)
    check_not_changed()


def check_not_changed():
    subprocess.check_call(['git', 'diff', '--exit-code'])


@task()
def fix_doctests():
    fd.main()


@task()
def compile_requirements(upgrade=False):
    if upgrade:
        extra = ['--upgrade']
    else:
        extra = []

    os.chdir(tools.ROOT)

    for f in glob(os.path.join('requirements', '*.in')):
        base, _ = os.path.splitext(f)
        pip_tool('pip-compile', *extra, f, '--output-file', base + '.txt')


@task()
def upgrade_requirements():
    compile_requirements(upgrade=True)


@task()
def check_requirements():
    compile_requirements()
    check_not_changed()


@task(if_changed=hp.HYPOTHESIS_PYTHON)
def documentation():
    os.chdir(hp.HYPOTHESIS_PYTHON)
    try:
        if hp.has_release():
            hp.update_changelog_and_version()
        pip_tool(
            'sphinx-build', '-W', '-b', 'html', '-d', 'docs/_build/doctrees',
            'docs', 'docs/_build/html'
        )
    finally:
        subprocess.check_call([
            'git', 'checkout', 'docs/changes.rst', 'src/hypothesis/version.py'
        ])


@task(if_changed=hp.HYPOTHESIS_PYTHON)
def doctest():
    os.chdir(hp.HYPOTHESIS_PYTHON)
    env = dict(os.environ)
    env['PYTHONPATH'] = 'src'

    pip_tool(
        'sphinx-build', '-W', '-b', 'doctest', '-d', 'docs/_build/doctrees',
        'docs', 'docs/_build/html', env=env,
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

    os.chdir(hp.HYPOTHESIS_PYTHON)
    env = dict(os.environ)
    python = install.python_executable(version)

    env['PATH'] = os.path.dirname(python) + ':' + env['PATH']
    print(env['PATH'])

    pip_tool('tox', '-e', task, env=env)


PY27 = '2.7.14'
PY34 = '3.4.8'
PY35 = '3.5.5'
PY36 = '3.6.5'
PYPY2 = 'pypy2.7-5.10.0'


@task()
def install_core():
    install.python_executable(PY27)
    install.python_executable(PY36)


ALIASES = {
    PYPY2: 'pypy',
}

for n in [PY27, PY34, PY35, PY36]:
    major, minor, patch = n.split('.')
    ALIASES[n] = 'python%s.%s' % (major, minor)


python_tests = task(if_changed=(hp.PYTHON_SRC, hp.PYTHON_TESTS))


@python_tests
def check_py27():
    run_tox('py27-full', PY27)


@python_tests
def check_py34():
    run_tox('py34-full', PY34)


@python_tests
def check_py35():
    run_tox('py35-full', PY35)


@python_tests
def check_py36():
    run_tox('py36-full', PY36)


@python_tests
def check_pypy():
    run_tox('pypy-full', PYPY2)


@python_tests
def check_py27_typing():
    run_tox('py27typing', PY27)


@python_tests
def check_pypy_with_tracer():
    run_tox('pypy-with-tracer', PYPY2)


def standard_tox_task(name):
    TASKS['check-' + name] = python_tests(lambda: run_tox(name, PY36))


standard_tox_task('nose')
standard_tox_task('pytest28')
standard_tox_task('faker070')
standard_tox_task('faker-latest')
standard_tox_task('django20')
standard_tox_task('django111')

for n in [19, 20, 21, 22, 23]:
    standard_tox_task('pandas%d' % (n,))

standard_tox_task('coverage')
standard_tox_task('pure-tracer')


@task()
def check_quality():
    run_tox('quality', PY36)
    run_tox('quality2', PY27)


examples_task = task(if_changed=(hp.PYTHON_SRC, os.path.join(
    hp.HYPOTHESIS_PYTHON, 'examples')
))


@examples_task
def check_examples2():
    run_tox('examples2', PY27)


@examples_task
def check_examples3():
    run_tox('examples2', PY36)


@python_tests
def check_unicode():
    run_tox('unicode', PY27)


@task()
def check_whole_repo_tests():
    install.ensure_shellcheck()
    subprocess.check_call([
        sys.executable, '-m', 'pytest', tools.REPO_TESTS
    ])


@task()
def shell():
    import IPython
    IPython.start_ipython([])


def ruby_task(fn):
    return task(if_changed=(hr.HYPOTHESIS_RUBY,))(fn)


@ruby_task
def lint_ruby():
    hr.rake_task('checkformat')


@ruby_task
def check_ruby_tests():
    hr.rake_task('test')


@task()
def python(*args):
    os.execv(sys.executable, (sys.executable,) + args)


@task()
def bundle(*args):
    hr.bundle(*args)


if __name__ == '__main__':
    if 'SNAKEPIT' not in os.environ:
        print(
            'This module should not be executed directly, but instead via '
            'build.sh (which sets up its environment)'
        )
        sys.exit(1)

    if len(sys.argv) > 1:
        task_to_run = sys.argv[1]
        args = sys.argv[2:]
    else:
        task_to_run = os.environ.get('TASK')
        args = ()

    if task_to_run is None:
        print(
            'No task specified. Either pass the task to run as an '
            'argument or as an environment variable TASK.')
        sys.exit(1)

    try:
        TASKS[task_to_run](*args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
