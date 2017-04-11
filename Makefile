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

TOOLS=$(BUILD_RUNTIMES)/tools

TOX=$(TOOLS)/tox
SPHINX_BUILD=$(TOOLS)/sphinx-build
ISORT=$(TOOLS)/isort
FLAKE8=$(TOOLS)/flake8
PYFORMAT=$(TOOLS)/pyformat
RSTLINT=$(TOOLS)/rst-lint

BROKEN_VIRTUALENV=$(BUILD_RUNTIMES)/virtualenvs/broken
TOOL_VIRTUALENV=$(BUILD_RUNTIMES)/virtualenvs/tools
TOOL_PYTHON=$(TOOL_VIRTUALENV)/bin/python
TOOL_PIP=$(TOOL_VIRTUALENV)/bin/pip

FILES_TO_FORMAT=find src tests -name '*.py' -not \( \
								-path '*/vendor/*' -or -name test_lambda_formatting.py \
								\)

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

$(TOOL_VIRTUALENV): $(PY34) requirements/tools.txt
	rm -rf $(TOOL_VIRTUALENV)
	$(PY34) -m virtualenv $(TOOL_VIRTUALENV)
	$(TOOL_PIP) install -r requirements/tools.txt

$(TOOLS): $(TOOL_VIRTUALENV)
	mkdir -p $(TOOLS)

install-tools: $(TOOLS)

format: $(PYFORMAT) $(ISORT)
	$(FILES_TO_FORMAT) | $(TOOL_PYTHON) scripts/enforce_header.py
	# isort will sort packages differently depending on whether they're installed
	$(FILES_TO_FORMAT) | xargs env -i PATH="$(PATH)" $(ISORT) -p hypothesis -ls -m 2 -w 75 \
			-a "from __future__ import absolute_import, print_function, division" \
			-rc src tests examples
	$(FILES_TO_FORMAT) | xargs $(PYFORMAT) -i

lint: $(FLAKE8)
	$(FLAKE8) src tests --exclude=compat.py,test_reflection.py,test_imports.py,tests/py2,test_lambda_formatting.py --ignore=E731,E721

check-format: format
	find src tests -name "*.py" | xargs $(TOOL_PYTHON) scripts/check_encoding_header.py
	git diff --exit-code

install-core: $(PY27) $(PYPY) $(PY36) $(TOX)

check-py27: $(PY27) $(TOX)
	$(TOX) -e py27-full

check-py273: $(PY273) $(TOX)
	$(TOX) -e oldpy27

check-py33: $(PY33) $(TOX)
	$(TOX) -e py33-full

check-py34: $(py34) $(TOX)
	$(TOX) -e py34-full

check-py35: $(PY35) $(TOX)
	$(TOX) -e py35-full

check-py36: $(PY36) $(TOX)
	$(TOX) -e py36-full

check-pypy: $(PYPY) $(TOX)
	$(TOX) -e pypy-full

check-nose: $(TOX) $(PY35)
	$(TOX) -e nose

check-pytest30: $(TOX) $(PY35)
	$(TOX) -e pytest30

check-pytest28: $(TOX) $(PY35)
	$(TOX) -e pytest28

check-quality: $(PY36) $(TOX)
	$(TOX) -e quality

check-ancient-pip: $(PY273)
	scripts/check-ancient-pip.sh $(PY273)


check-pytest: check-pytest28 check-pytest30

check-faker070: $(TOX) $(PY35)
	$(TOX) -e faker070

check-faker071: $(TOX) $(PY35)
	$(TOX) -e faker071

check-django18: $(TOX) $(PY35)
	$(TOX) -e django18

check-django110: $(TOX) $(PY35)
	$(TOX) -e django110

check-django111: $(TOX) $(PY35)
	$(TOX) -e django111

check-django: check-django18 check-django110 check-django111

check-examples2: $(TOX) $(PY27)
	$(TOX) -e examples2

check-examples3: $(TOX) $(PY35)
	$(TOX) -e examples3

check-coverage: $(TOX) $(PY35)
	$(TOX) -e coverage

check-unicode: $(TOX) $(PY27)
	$(TOX) -e unicode

check-noformat: check-coverage check-py26 check-py27 check-py33 check-py34 check-py35 check-pypy check-django check-pytest

check: check-format check-noformat

check-fast: lint $(PY35) $(PYPY) $(TOX)
	$(TOX) -e pypy-brief
	$(TOX) -e py35-brief
	$(TOX) -e py26-brief
	$(TOX) -e py35-prettyquick

check-rst: $(RSTLINT)
	$(RSTLINT) CONTRIBUTING.rst
	$(RSTLINT) README.rst

$(TOX): $(PY35) tox.ini $(TOOLS)
	rm -f $(TOX)
	ln -sf $(TOOL_VIRTUALENV)/bin/tox $(TOX)
	touch $(TOOL_VIRTUALENV)/bin/tox $(TOX)

$(SPHINX_BUILD): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/sphinx-build $(SPHINX_BUILD)

$(PYFORMAT): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/pyformat $(PYFORMAT)

$(ISORT): $(TOOLS)
	ln -sf $(TOOL_VIRTUALENV)/bin/isort $(ISORT)

$(RSTLINT): $(TOOL_VIRTUALENV)
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
