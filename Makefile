.PHONY: clean documentation


DEVELOPMENT_DATABASE?=postgres://whereshouldilive@localhost/whereshouldilive_dev
SPHINXBUILD   = $(DEV_PYTHON) -m sphinx
SPHINX_BUILDDIR      = docs/_build
ALLSPHINXOPTS   = -d $(SPHINX_BUILDDIR)/doctrees docs -W

export BUILD_RUNTIMES?=$(HOME)/.cache/hypothesis-build-runtimes
export TOX_WORK_DIR=$(BUILD_RUNTIMES)/.tox
export COVERAGE_FILE=$(BUILD_RUNTIMES)/.coverage

PY27=$(BUILD_RUNTIMES)/snakepit/python2.7
PY273=$(BUILD_RUNTIMES)/snakepit/python2.7.3
PY33=$(BUILD_RUNTIMES)/snakepit/python3.3
PY34=$(BUILD_RUNTIMES)/snakepit/python3.4
PY35=$(BUILD_RUNTIMES)/snakepit/python3.5
PY36=$(BUILD_RUNTIMES)/snakepit/python3.6
PYPY=$(BUILD_RUNTIMES)/snakepit/pypy

BEST_PY3=$(PY36)

TOOLS=$(BUILD_RUNTIMES)/tools

TOX=$(TOOLS)/tox
SPHINX_BUILD=$(TOOLS)/sphinx-build
ISORT=$(TOOLS)/isort
FLAKE8=$(TOOLS)/flake8
PYFORMAT=$(TOOLS)/pyformat
RSTLINT=$(TOOLS)/rst-lint

TOOL_VIRTUALENV:=$(BUILD_RUNTIMES)/virtualenvs/tools-$(shell scripts/tool-hash.py tools)

TOOL_PYTHON=$(TOOL_VIRTUALENV)/bin/python
TOOL_PIP=$(TOOL_VIRTUALENV)/bin/pip

BENCHMARK_VIRTUALENV:=$(BUILD_RUNTIMES)/virtualenvs/benchmark-$(shell scripts/tool-hash.py benchmark)
BENCHMARK_PYTHON=$(BENCHMARK_VIRTUALENV)/bin/python

FILES_TO_FORMAT=$(BEST_PY3) scripts/files-to-format.py


export PATH:=$(BUILD_RUNTIMES)/snakepit:$(TOOLS):$(PATH)
export LC_ALL=en_US.UTF-8

$(PY27):
	scripts/retry.sh scripts/install.sh 2.7

$(PY273):
	scripts/retry.sh scripts/install.sh 2.7.3

$(PY33):
	scripts/retry.sh scripts/install.sh 3.3

$(PY34):
	scripts/retry.sh scripts/install.sh 3.4

$(PY35):
	scripts/retry.sh scripts/install.sh 3.5

$(PY36):
	scripts/retry.sh scripts/install.sh 3.6


$(PYPY):
	scripts/retry.sh scripts/install.sh pypy

$(TOOL_VIRTUALENV): $(BEST_PY3)
	rm -rf $(BUILD_RUNTIMES)/virtualenvs/tools-*
	$(BEST_PY3) -m virtualenv $(TOOL_VIRTUALENV)
	$(TOOL_PIP) install -r requirements/tools.txt

$(BENCHMARK_VIRTUALENV): $(BEST_PY3)
	rm -rf $(BUILD_RUNTIMES)/virtualenvs/benchmark-*
	$(BEST_PY3) -m virtualenv $(BENCHMARK_VIRTUALENV)
	$(BENCHMARK_PYTHON) -m pip install -r requirements/benchmark.txt

$(TOOLS): $(TOOL_VIRTUALENV)
	mkdir -p $(TOOLS)

install-tools: $(TOOLS)

format: $(PYFORMAT) $(ISORT)
	$(FILES_TO_FORMAT) | xargs $(TOOL_PYTHON) scripts/enforce_header.py
	# isort will sort packages differently depending on whether they're installed
	$(FILES_TO_FORMAT) | xargs env -i PATH="$(PATH)" $(ISORT) -p hypothesis -ls -m 2 -w 75 \
			-a "from __future__ import absolute_import, print_function, division" \
			-rc src tests examples
	$(FILES_TO_FORMAT) | xargs $(PYFORMAT) -i

lint: $(FLAKE8)
	$(FLAKE8) src tests --exclude=compat.py,test_reflection.py,test_imports.py,tests/py2,test_lambda_formatting.py --ignore=E731,E721

check-untagged: $(BEST_PY3)
	$(BEST_PY3) scripts/check-untagged.py

check-changelog: $(BEST_PY3)
	$(BEST_PY3) scripts/check-changelog.py

deploy: $(TOOL_VIRTUALENV)
	$(TOOL_PYTHON) scripts/deploy.py

check-format: format
	find src tests -name "*.py" | xargs $(TOOL_PYTHON) scripts/check_encoding_header.py
	git diff --exit-code

install-core: $(PY27) $(PYPY) $(BEST_PY3) $(TOX)

STACK=$(HOME)/.local/bin/stack
GHC=$(HOME)/.local/bin/ghc
SHELLCHECK=$(HOME)/.local/bin/shellcheck

$(STACK):
	mkdir -p ~/.local/bin
	curl -L https://www.stackage.org/stack/linux-x86_64 | tar xz --wildcards --strip-components=1 -C $(HOME)/.local/bin '*/stack'

$(GHC): $(STACK)
	$(STACK) setup

$(SHELLCHECK): $(GHC)
	$(STACK) install ShellCheck

check-shellcheck: $(SHELLCHECK)
	shellcheck scripts/*.sh

check-py27: $(PY27) $(TOX)
	$(TOX) -e py27-full

check-py273: $(PY273) $(TOX)
	$(TOX) -e oldpy27

check-py33: $(PY33) $(TOX)
	$(TOX) -e py33-full

check-py34: $(PY34) $(TOX)
	$(TOX) -e py34-full

check-py35: $(PY35) $(TOX)
	$(TOX) -e py35-full

check-py36: $(BEST_PY3) $(TOX)
	$(TOX) -e py36-full

check-pypy: $(PYPY) $(TOX)
	$(TOX) -e pypy-full

check-nose: $(TOX)
	$(TOX) -e nose

check-pytest30: $(TOX)
	$(TOX) -e pytest30

check-pytest28: $(TOX)
	$(TOX) -e pytest28

check-quality: $(TOX)
	$(TOX) -e quality

check-ancient-pip: $(PY273)
	scripts/check-ancient-pip.sh $(PY273)


check-pytest: check-pytest28 check-pytest30

check-faker070: $(TOX)
	$(TOX) -e faker070

check-faker071: $(TOX)
	$(TOX) -e faker071

check-django18: $(TOX)
	$(TOX) -e django18

check-django110: $(TOX)
	$(TOX) -e django110

check-django111: $(TOX)
	$(TOX) -e django111

check-django: check-django18 check-django110 check-django111

check-examples2: $(TOX) $(PY27)
	$(TOX) -e examples2

check-examples3: $(TOX)
	$(TOX) -e examples3

check-coverage: $(TOX)
	$(TOX) -e coverage

check-unicode: $(TOX) $(PY27)
	$(TOX) -e unicode

check-noformat: check-coverage check-py26 check-py27 check-py33 check-py34 check-py35 check-pypy check-django check-pytest

check: check-format check-noformat

check-fast: lint $(PYPY) $(PY36) $(TOX)
	$(TOX) -e pypy-brief
	$(TOX) -e py36-prettyquick

check-rst: $(RSTLINT) $(FLAKE8)
	$(RSTLINT) *.rst
	$(FLAKE8) --select=W191,W291,W292,W293,W391 *.rst docs/*.rst

secret.tar.enc: deploy_key .pypirc
	rm -f secrets.tar secrets.tar.enc
	tar -cf secrets.tar deploy_key .pypirc
	travis encrypt-file secrets.tar
	rm secrets.tar

check-benchmark: $(BENCHMARK_VIRTUALENV)
	PYTHONPATH=src $(BENCHMARK_PYTHON) scripts/benchmarks.py --check

build-new-benchmark-data: $(BENCHMARK_VIRTUALENV)
	PYTHONPATH=src $(BENCHMARK_PYTHON) scripts/benchmarks.py --skip-existing

update-improved-benchmark-data: $(BENCHMARK_VIRTUALENV)
	PYTHONPATH=src $(BENCHMARK_PYTHON) scripts/benchmarks.py --update=improved

update-all-benchmark-data: $(BENCHMARK_VIRTUALENV)
	PYTHONPATH=src $(BENCHMARK_PYTHON) scripts/benchmarks.py --update=all

update-benchmark-headers: $(BENCHMARK_VIRTUALENV)
	PYTHONPATH=src $(BENCHMARK_PYTHON) scripts/benchmarks.py --only-update-headers

$(TOX): $(BEST_PY3) tox.ini $(TOOLS)
	rm -f $(TOX)
	ln -sf $(TOOL_VIRTUALENV)/bin/tox $(TOX)
	touch $(TOOL_VIRTUALENV)/bin/tox $(TOX)

$(SPHINX_BUILD): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/sphinx-build $(SPHINX_BUILD)

$(PYFORMAT): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/pyformat $(PYFORMAT)

$(ISORT): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/isort $(ISORT)

$(RSTLINT): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/rst-lint $(RSTLINT)

$(FLAKE8): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/flake8 $(FLAKE8)


clean:
	rm -rf .tox
	rm -rf .hypothesis
	rm -rf docs/_build
	rm -rf $(TOOLS)
	rm -rf $(BUILD_RUNTIMES)/snakepit
	rm -rf $(BUILD_RUNTIMES)/virtualenvs
	find src tests -name "*.pyc" -delete
	find src tests -name "__pycache__" -delete

documentation: $(SPHINX_BUILD) docs/*.rst
	PYTHONPATH=src $(SPHINX_BUILD) -W -b html -d docs/_build/doctrees docs docs/_build/html
	PYTHONPATH=src $(SPHINX_BUILD) -W -b doctest -d docs/_build/doctrees docs docs/_build/html
