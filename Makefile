.PHONY: clean documentation


DEVELOPMENT_DATABASE?=postgres://whereshouldilive@localhost/whereshouldilive_dev
SPHINXBUILD   = $(DEV_PYTHON) -m sphinx
SPHINX_BUILDDIR      = docs/_build
ALLSPHINXOPTS   = -d $(SPHINX_BUILDDIR)/doctrees docs -W

export BUILD_RUNTIMES?=$(HOME)/.cache/hypothesis-build-runtimes
export TOX_WORK_DIR=$(BUILD_RUNTIMES)/.tox
export COVERAGE_FILE=$(BUILD_RUNTIMES)/.coverage

PY26=$(BUILD_RUNTIMES)/snakepit/python2.6
PY27=$(BUILD_RUNTIMES)/snakepit/python2.7
PY273=$(BUILD_RUNTIMES)/snakepit/python2.7.3
PY33=$(BUILD_RUNTIMES)/snakepit/python3.3
PY34=$(BUILD_RUNTIMES)/snakepit/python3.4
PY35=$(BUILD_RUNTIMES)/snakepit/python3.5
PYPY=$(BUILD_RUNTIMES)/snakepit/pypy

TOOLS=$(BUILD_RUNTIMES)/tools

TOX=$(TOOLS)/tox
SPHINX_BUILD=$(TOOLS)/sphinx-build
SPHINX_AUTOBUILD=$(TOOLS)/sphinx-autobuild
ISORT=$(TOOLS)/isort
FLAKE8=$(TOOLS)/flake8
PYFORMAT=$(TOOLS)/pyformat

BROKEN_VIRTUALENV=$(BUILD_RUNTIMES)/virtualenvs/broken
TOOL_VIRTUALENV=$(BUILD_RUNTIMES)/virtualenvs/tools
ISORT_VIRTUALENV=$(BUILD_RUNTIMES)/virtualenvs/isort
TOOL_PYTHON=$(TOOL_VIRTUALENV)/bin/python
TOOL_PIP=$(TOOL_VIRTUALENV)/bin/pip
TOOL_INSTALL=$(TOOL_PIP) install --upgrade

export PATH:=$(BUILD_RUNTIMES)/snakepit:$(TOOLS):$(PATH)
export LC_ALL=en_US.UTF-8

$(PY26):
	scripts/retry.sh scripts/install.sh 2.6

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

$(PYPY):
	scripts/retry.sh scripts/install.sh pypy

$(TOOL_VIRTUALENV): $(PY34)
	$(PY34) -m virtualenv $(TOOL_VIRTUALENV)
	mkdir -p $(TOOLS)

$(TOOLS): $(TOOL_VIRTUALENV)

install-tools: $(TOOLS)

$(ISORT_VIRTUALENV): $(PY34)
	$(PY34) -m virtualenv $(ISORT_VIRTUALENV)

format: $(PYFORMAT) $(ISORT)
	$(TOOL_PYTHON) scripts/enforce_header.py
	# isort will sort packages differently depending on whether they're installed
	$(ISORT_VIRTUALENV)/bin/python -m pip install django pytz pytest fake-factory numpy flaky
	find src tests hypothesislegacysupport examples -name '*.py' | xargs  env -i \
            PATH="$(PATH)" $(ISORT) -p hypothesis -ls -m 2 -w 75 \
			-a  "from __future__ import absolute_import, print_function, division" \
			-rc src tests examples hypothesislegacysupport/src
	find src tests hypothesislegacysupport examples -name '*.py' | xargs $(PYFORMAT) -i

lint: $(FLAKE8)
	$(FLAKE8) src tests --exclude=compat.py,test_reflection.py,test_imports.py,tests/py2 --ignore=E731,E721

check-format: format
	find src tests -name "*.py" | xargs $(TOOL_PYTHON) scripts/check_encoding_header.py
	git diff --exit-code

check-py26: $(PY26) $(TOX)
	$(TOX) -e py26-full

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

check-pypy: $(PYPY) $(TOX)
	$(TOX) -e pypy-full

check-nose: $(TOX) $(PY35)
	$(TOX) -e nose

check-pytest27: $(TOX) $(PY35)
	$(TOX) -e pytest27

check-pytest26: $(TOX) $(PY35)
	$(TOX) -e pytest26

check-ancient-pip: $(PY273)
	scripts/check-ancient-pip.sh $(PY273)
	

check-pytest: check-pytest26 check-pytest27

check-fakefactory052: $(TOX) $(PY35)
	$(TOX) -e fakefactory052

check-fakefactory053: $(TOX) $(PY35)
	$(TOX) -e fakefactory053

check-django17: $(TOX) $(PY35)
	$(TOX) -e django17

check-django18: $(TOX) $(PY35)
	$(TOX) -e django18

check-django19: $(TOX) $(PY35)
	$(TOX) -e django19

check-django: check-django17 check-django18 check-django19

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

check-fast: lint $(PY26) $(PY35) $(PYPY) $(TOX)
	$(TOX) -e pypy-brief
	$(TOX) -e py35-brief
	$(TOX) -e py26-brief
	$(TOX) -e py35-prettyquick

$(TOX): $(PY35) tox.ini $(TOOLS)
	rm -f $(TOX)
	$(TOOL_INSTALL) tox
	ln -sf $(TOOL_VIRTUALENV)/bin/tox $(TOX)
	touch $(TOOL_VIRTUALENV)/bin/tox $(TOX)

$(SPHINX_BUILD): $(TOOL_VIRTUALENV)
	$(TOOL_PYTHON) -m pip install sphinx sphinx-rtd-theme
	ln -sf $(TOOL_VIRTUALENV)/bin/sphinx-build $(SPHINX_BUILD)

$(SPHINX_AUTOBUILD): $(TOOL_VIRTUALENV)
	$(TOOL_PYTHON) -m pip install sphinx-autobuild
	ln -sf $(TOOL_VIRTUALENV)/bin/sphinx-autobuild $(SPHINX_AUTOBUILD)

$(PYFORMAT): $(TOOL_VIRTUALENV)
	$(TOOL_INSTALL) pyformat
	ln -sf $(TOOL_VIRTUALENV)/bin/pyformat $(PYFORMAT)

$(ISORT): $(ISORT_VIRTUALENV)
	$(ISORT_VIRTUALENV)/bin/python -m pip install isort==4.1.0
	ln -sf $(ISORT_VIRTUALENV)/bin/isort $(ISORT)

$(FLAKE8): $(TOOL_VIRTUALENV)
	$(TOOL_INSTALL) flake8
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
	$(SPHINX_BUILD) -W -b html -d docs/_build/doctrees docs docs/_build/html
