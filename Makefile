
.PHONY: clean documentation


ROOT_DIR:=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))

HYPOTHESIS_PYTHON=$(ROOT_DIR)/hypothesis-python


DEVELOPMENT_DATABASE?=postgres://whereshouldilive@localhost/whereshouldilive_dev
SPHINXBUILD   = $(DEV_PYTHON) -m sphinx
SPHINX_BUILDDIR      = docs/_build
ALLSPHINXOPTS   = -d $(SPHINX_BUILDDIR)/doctrees docs -W

export BUILD_RUNTIMES?=$(HOME)/.cache/hypothesis-build-runtimes
export TOX_WORK_DIR=$(BUILD_RUNTIMES)/.tox
export COVERAGE_FILE=$(BUILD_RUNTIMES)/.coverage

PY27=$(BUILD_RUNTIMES)/snakepit/python2.7
PY273=$(BUILD_RUNTIMES)/snakepit/python2.7.3
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
PIPCOMPILE=$(TOOLS)/pip-compile

TOOL_VIRTUALENV:=$(BUILD_RUNTIMES)/virtualenvs/tools-$(shell scripts/tool-hash.py tools)

TOOL_PYTHON=$(TOOL_VIRTUALENV)/bin/python
TOOL_PIP=$(TOOL_VIRTUALENV)/bin/pip

FILES_TO_FORMAT=$(BEST_PY3) scripts/files-to-format.py


define run_tox
	cd $(HYPOTHESIS_PYTHON); $(TOX) --recreate -e $(1)
endef


export PATH:=$(BUILD_RUNTIMES)/snakepit:$(TOOLS):$(PATH)
export LC_ALL=en_US.UTF-8

$(PY27):
	scripts/retry.sh scripts/install.sh 2.7

$(PY273):
	scripts/retry.sh scripts/install.sh 2.7.3

$(PY34):
	scripts/retry.sh scripts/install.sh 3.4

$(PY35):
	scripts/retry.sh scripts/install.sh 3.5

$(PY36):
	scripts/retry.sh scripts/install.sh 3.6


$(PYPY):
	scripts/retry.sh scripts/install.sh pypy

$(TOOL_VIRTUALENV): $(BEST_PY3)
	$(BEST_PY3) -m virtualenv $(TOOL_VIRTUALENV)
	$(TOOL_PIP) install -r requirements/tools.txt

$(TOOLS): $(TOOL_VIRTUALENV)
	mkdir -p $(TOOLS)

install-tools: $(TOOLS)

format: $(PYFORMAT) $(ISORT)
	$(FILES_TO_FORMAT) | xargs $(TOOL_PYTHON) scripts/enforce_header.py
	# isort will sort packages differently depending on whether they're installed
	$(FILES_TO_FORMAT) | xargs env -i PATH="$(PATH)" $(ISORT) -p hypothesis -ls -m 2 -w 75 \
			-a "from __future__ import absolute_import, print_function, division"
	$(FILES_TO_FORMAT) | xargs $(PYFORMAT) -i

lint: $(FLAKE8)
	$(FLAKE8) src tests


check-pyup-yml: $(TOOL_VIRTUALENV)
	$(TOOL_PYTHON) scripts/validate_pyup.py

check-release-file: $(BEST_PY3)
	$(BEST_PY3) scripts/check-release-file.py

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
	$(call run_tox,py27-full)

check-py273: $(PY273) $(TOX)
	$(call run_tox,oldpy27)

check-py27-typing: $(PY27) $(TOX)
	$(call run_tox,py27typing)

check-py34: $(PY34) $(TOX)
	$(call run_tox,py34-full)

check-py35: $(PY35) $(TOX)
	$(call run_tox,py35-full)

check-py36: $(BEST_PY3) $(TOX)
	$(call run_tox,py36-full)

check-pypy: $(PYPY) $(TOX)
	$(call run_tox,pypy-full)

check-pypy-with-tracer: $(PYPY) $(TOX)
	$(call run_tox,pypy-with-tracer)

check-nose: $(TOX)
	$(call run_tox,nose)

check-pytest30: $(TOX)
	$(call run_tox,pytest30)

check-pytest28: $(TOX)
	$(call run_tox,pytest28)

check-quality: $(TOX) $(PY27)
	$(call run_tox,quality)
	$(call run_tox,quality2)

check-ancient-pip: $(PY273)
	scripts/check-ancient-pip.sh $(PY273)


check-pytest: check-pytest28 check-pytest30

check-faker070: $(TOX)
	$(call run_tox,faker070)

check-faker-latest: $(TOX)
	$(call run_tox,faker-latest)

check-django111: $(TOX)
	$(call run_tox,django111)

check-django20: $(BEST_PY3) $(TOX)
	$(call run_tox,django20)

check-django: check-django111 check-django20

check-pandas19: $(TOX)
	$(call run_tox,pandas19)

check-pandas20: $(TOX)
	$(call run_tox,pandas20)

check-pandas21: $(TOX)
	$(call run_tox,pandas21)

check-pandas22: $(TOX)
	$(call run_tox,pandas22)

check-examples2: $(TOX) $(PY27)
	$(call run_tox,examples2)

check-examples3: $(TOX)
	$(call run_tox,examples3)

check-coverage: $(TOX)
	$(call run_tox,coverage)

check-pure-tracer: $(TOX)
	$(call run_tox,pure-tracer)

check-unicode: $(TOX) $(PY27)
	$(call run_tox,unicode)

check-noformat: check-coverage check-py26 check-py27 check-py34 check-py35 check-pypy check-django check-pytest

check: check-format check-noformat

check-fast: lint $(PYPY) $(PY36) $(TOX)
	$(call run_tox,pypy-brief)
	$(call run_tox,py36-prettyquick)

check-rst: $(RSTLINT) $(FLAKE8)
	$(RSTLINT) CONTRIBUTING.rst README.rst
	$(RSTLINT) guides/*.rst
	$(FLAKE8) --select=W191,W291,W292,W293,W391 *.rst docs/*.rst

compile-requirements: $(PIPCOMPILE)
	$(PIPCOMPILE) requirements/test.in --output-file requirements/test.txt
	$(PIPCOMPILE) requirements/tools.in --output-file requirements/tools.txt
	$(PIPCOMPILE) requirements/typing.in --output-file requirements/typing.txt
	$(PIPCOMPILE) requirements/coverage.in --output-file requirements/coverage.txt

upgrade-requirements:
	$(PIPCOMPILE) --upgrade requirements/test.in --output-file requirements/test.txt
	$(PIPCOMPILE) --upgrade requirements/tools.in --output-file requirements/tools.txt
	$(PIPCOMPILE) --upgrade requirements/typing.in --output-file requirements/typing.txt
	$(PIPCOMPILE) --upgrade requirements/coverage.in --output-file requirements/coverage.txt

check-requirements: compile-requirements
	git diff --exit-code

secrets.tar.enc: deploy_key .pypirc
	rm -f secrets.tar secrets.tar.enc
	tar -cf secrets.tar deploy_key .pypirc
	travis encrypt-file secrets.tar
	rm secrets.tar

$(TOX): $(BEST_PY3) $(HYPOTHESIS_PYTHON)/tox.ini $(TOOLS)
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

$(PIPCOMPILE): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/pip-compile $(PIPCOMPILE)


clean:
	rm -rf .tox
	rm -rf .hypothesis
	rm -rf docs/_build
	rm -rf $(TOOLS)
	rm -rf $(BUILD_RUNTIMES)/snakepit
	rm -rf $(BUILD_RUNTIMES)/virtualenvs
	find src tests -name "*.pyc" -delete
	find src tests -name "__pycache__" -delete

.PHONY: RELEASE.rst
RELEASE.rst:

documentation: $(SPHINX_BUILD) docs/*.rst RELEASE.rst
	scripts/build-documentation.sh $(SPHINX_BUILD) $(PY36)

doctest: $(SPHINX_BUILD) docs/*.rst
	PYTHONPATH=src $(SPHINX_BUILD) -W -b doctest -d docs/_build/doctrees docs docs/_build/html

fix_doctests: $(TOOL_VIRTUALENV)
	PYTHONPATH=src $(TOOL_PYTHON) scripts/fix_doctests.py
