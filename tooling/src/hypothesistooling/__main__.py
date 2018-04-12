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
import json
import random
import shutil
import subprocess
from glob import glob
from time import time, sleep
from datetime import datetime
from collections import defaultdict

import yaml
from pyup.config import Config

import hypothesistooling as tools
import hypothesistooling.installers as install
from hypothesistooling import fix_doctests as fd
from hypothesistooling.scripts import pip_tool, run_script

TASKS = {}


def task(fn):
    name = fn.__name__.replace('_', '-')
    TASKS[name] = fn
    return fn


@task
def lint():
    os.chdir(tools.HYPOTHESIS_PYTHON)
    pip_tool('flake8', 'src', 'tests', '--config', os.path.join(
        tools.ROOT, ".flake8"
    ))


@task
def check_pyup_yaml():
    with open(tools.PYUP_FILE, 'r') as i:
        data = yaml.safe_load(i.read())
    config = Config()
    config.update_config(data)

    if not config.is_valid_schedule():
        print('Schedule %r is invalid' % (config.schedule,))
        sys.exit(1)


@task
def validate_branch_check():
    with open('branch-check') as i:
        data = [
            json.loads(l) for l in i
        ]

    checks = defaultdict(set)

    for d in data:
        checks[d['name']].add(d['value'])

    always_true = []
    always_false = []

    for c, vs in sorted(checks.items()):
        if len(vs) < 2:
            v = list(vs)[0]
            assert v in (False, True)
            if v:
                always_true.append(c)
            else:
                always_false.append(c)

    failure = always_true or always_false

    if failure:
        print('Some branches were not properly covered.')
        print()

    if always_true:
        print('The following were always True:')
        print()
        for c in always_true:
            print('  * %s' % (c,))
    if always_false:
        print('The following were always False:')
        print()
        for c in always_false:
            print('  * %s' % (c,))
    if failure:
        sys.exit(1)


DIST = os.path.join(tools.HYPOTHESIS_PYTHON, 'dist')
PENDING_STATUS = ('started', 'created')


@task
def deploy(self):
    os.chdir(tools.HYPOTHESIS_PYTHON)

    last_release = tools.latest_version()

    print('Current version: %s. Latest released version: %s' % (
        tools.__version__, last_release
    ))

    HEAD = tools.hash_for_name('HEAD')
    MASTER = tools.hash_for_name('origin/master')
    print('Current head:', HEAD)
    print('Current master:', MASTER)

    on_master = tools.is_ancestor(HEAD, MASTER)
    has_release = tools.has_release()

    if has_release:
        print('Updating changelog and version')
        tools.update_for_pending_release()

    print('Building an sdist...')

    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    subprocess.check_output([
        sys.executable, 'setup.py', 'sdist', '--dist-dir', DIST,
    ])

    if not on_master:
        print('Not deploying due to not being on master')
        sys.exit(0)

    if not has_release:
        print('Not deploying due to no release')
        sys.exit(0)

    start_time = time()

    prev_pending = None

    # We time out after an hour, which is a stupidly long time and it should
    # never actually take that long: A full Travis run only takes about 20-30
    # minutes! This is really just here as a guard in case something goes
    # wrong and we're not paying attention so as to not be too mean to Travis..
    while time() <= start_time + 60 * 60:
        jobs = tools.build_jobs()

        failed_jobs = [
            (k, v)
            for k, vs in jobs.items()
            if k not in PENDING_STATUS + ('passed',)
            for v in vs
        ]

        if failed_jobs:
            print('Failing this due to failure of jobs %s' % (
                ', '.join('%s(%s)' % (s, j) for j, s in failed_jobs),
            ))
            sys.exit(1)
        else:
            pending = [j for s in PENDING_STATUS for j in jobs.get(s, ())]
            try:
                # This allows us to test the deploy job for a build locally.
                pending.remove('deploy')
            except ValueError:
                pass
            if pending:
                still_pending = set(pending)
                if prev_pending is None:
                    print('Waiting for the following jobs to complete:')
                    for p in sorted(still_pending):
                        print(' * %s' % (p,))
                    print()
                else:
                    completed = prev_pending - still_pending
                    if completed:
                        print('%s completed since last check.' % (
                            ', '.join(sorted(completed)),))
                prev_pending = still_pending
                naptime = 10.0 * (2 + random.random())
                print('Waiting %.2fs for %d more job%s to complete' % (
                    naptime, len(pending), 's' if len(pending) > 1 else '',))
                sleep(naptime)
            else:
                break
    else:
        print("We've been waiting for an hour. That seems bad. Failing now.")
        sys.exit(1)

    print('Looks good to release!')

    if os.environ.get('TRAVIS_SECURE_ENV_VARS', None) != 'true':
        print("But we don't have the keys to do it")
        sys.exit(0)

    print('Decrypting secrets')
    tools.decrypt_secrets()

    print('Release seems good. Pushing to github now.')

    tools.create_tag_and_push()

    print('Now uploading to pypi.')

    subprocess.check_call([
        sys.executable, '-m', 'twine', 'upload',
        '--config-file', tools.PYPIRC,
        os.path.join(DIST, '*'),
    ])

    sys.exit(0)


@task
def check_release_file():
    if tools.has_source_changes():
        if not tools.has_release():
            print(
                'There are source changes but no RELEASE.rst. Please create '
                'one to describe your changes.'
            )
            sys.exit(1)
        tools.parse_release_file()


@task
def check_shellcheck():
    install.ensure_shellcheck()
    subprocess.check_call([install.SHELLCHECK] + [
        f for f in tools.all_files()
        if f.endswith('.sh')
    ])


@task
def check_rst():
    rst = glob('*.rst') + glob('guides/*.rst')
    docs = glob('hypothesis-python/docs/*.rst')

    pip_tool('rst-lint', *rst)
    pip_tool('flake8',  '--select=W191,W291,W292,W293,W391', *(rst + docs))


@task
def check_secrets():
    if os.environ.get('TRAVIS_SECURE_ENV_VARS', None) != 'true':
        sys.exit(0)

    tools.decrypt_secrets()

    assert os.path.exists(tools.DEPLOY_KEY)


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


@task
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


@task
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


@task
def fix_doctests():
    fd.main()


@task
def compile_requirements(upgrade=False):
    if upgrade:
        extra = ['--upgrade']
    else:
        extra = []

    os.chdir(tools.ROOT)

    for f in glob(os.path.join('requirements', '*.in')):
        base, _ = os.path.splitext(f)
        pip_tool('pip-compile', *extra, f, '--output-file', base + '.txt')


@task
def upgrade_requirements():
    compile_requirements(upgrade=True)


@task
def check_requirements():
    compile_requirements()
    check_not_changed()


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


@task
def documentation():
    os.chdir(tools.HYPOTHESIS_PYTHON)
    try:
        update_changelog_for_docs()
        pip_tool(
            'sphinx-build', '-W', '-b', 'html', '-d', 'docs/_build/doctrees',
            'docs', 'docs/_build/html'
        )
    finally:
        subprocess.check_call([
            'git', 'checkout', 'docs/changes.rst', 'src/hypothesis/version.py'
        ])


@task
def doctest():
    os.chdir(tools.HYPOTHESIS_PYTHON)
    env = dict(os.environ)
    env['PYTHONPATH'] = 'src'

    pip_tool(
        'sphinx-build', '-W', '-b', 'doctest', '-d', 'docs/_build/doctrees',
        'docs', 'docs/_build/html', env=env,
    )


@task
def check_ancient_pip():
    os.chdir(tools.HYPOTHESIS_PYTHON)

    run_script(
        'check-ancient-pip.sh', install.python_executable('2.7.3')
    )


def run_tox(task, version):
    os.chdir(tools.HYPOTHESIS_PYTHON)
    env = dict(os.environ)
    python = install.python_executable(version)

    env['PATH'] = os.path.dirname(python) + ':' + env['PATH']
    print(env['PATH'])

    pip_tool('tox', '-e', task, env=env)


PY273 = '2.7.3'
PY27 = '2.7.14'
PY34 = '3.4.8'
PY35 = '3.5.5'
PY36 = '3.6.5'
PYPY2 = 'pypy2.7-5.10.0'


@task
def check_py273():
    python = tools.python_executable('2.7.3')

    # Create a fully qualified version of the name so e.g. tox
    # will pick it up for the more specific interpreter.
    linked_version = python + '2.7.3'
    try:
        os.symlink(python, linked_version)
    except FileExistsError:
        pass

    run_tox('oldpy27', PY273)


@task
def check_py27():
    run_tox('py27-full', PY27)


@task
def check_py34():
    run_tox('py34-full', PY34)


@task
def check_py35():
    run_tox('py35-full', PY35)


@task
def check_py36():
    run_tox('py36-full', PY36)


@task
def check_pypy():
    run_tox('pypy-full', PYPY2)


@task
def check_py27_typing():
    run_tox('py27typing', PY27)


@task
def check_pypy_with_tracer():
    run_tox('pypy-with-tracer', PYPY2)


def standard_tox_task(name):
    TASKS['check-' + name] = lambda: run_tox(name, PY36)


standard_tox_task('nose')
standard_tox_task('pytest28')
standard_tox_task('faker070')
standard_tox_task('faker-latest')
standard_tox_task('django20')
standard_tox_task('django111')

for n in [20, 21, 22, 23]:
    standard_tox_task('pandas%d' % (n,))

standard_tox_task('examples3')
standard_tox_task('coverage')
standard_tox_task('pure-tracer')


@task
def check_quality():
    run_tox('quality', PY36)
    run_tox('quality2', PY27)


@task
def check_examples2():
    run_tox('examples2', PY27)


@task
def check_unicode():
    run_tox('unicode', PY27)


if __name__ == '__main__':
    task_to_run = os.environ.get('TASK')
    if task_to_run is None:
        task_to_run = sys.argv[1]
    if not tools.should_run_ci_task(task_to_run):
        sys.exit(0)
    try:
        TASKS[task_to_run]()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except Exception:
        import pdb
        import traceback
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)
