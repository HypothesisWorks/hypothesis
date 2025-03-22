# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import importlib
import posixpath
from pathlib import Path

from sphinx.util.inventory import InventoryFile

import hypothesis.provisional
from hypothesis.strategies import __all__ as STRATEGY_EXPORTS
from hypothesistooling.__main__ import documentation
from hypothesistooling.projects import hypothesispython as hp


def test_documentation():
    documentation()


def get_all_exported_names():
    # start with hypothesis.strategies
    exports = {f"hypothesis.strategies.{name}" for name in STRATEGY_EXPORTS}
    # add any strategy exported by hypothesis.provisional
    exports |= {
        f"hypothesis.provisional.{name}"
        for name, value in vars(hypothesis.provisional).items()
        if getattr(value, "is_hypothesis_strategy_function", False)
        and not name.startswith("_")
    }

    # add anything exported from an extra
    for p in (hp.PYTHON_SRC / "hypothesis" / "extra").iterdir():
        # ignore private files/dirs. Also skip django, which requires setting up
        # a django app to import:
        #   django.core.exceptions.ImproperlyConfigured: Requested setting
        #   INSTALLED_APPS, but settings are not configured. You must either define
        #   the environment variable DJANGO_SETTINGS_MODULE or call settings.configure()
        #   before accessing settings.
        if p.name.startswith("_") or p.name == "django":
            continue

        module_name = f"hypothesis.extra.{p.stem}"
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        if hasattr(module, "__all__"):
            exports |= {f"{module_name}.{name}" for name in module.__all__}

    return exports


def test_documents_all_exported_strategies():
    hp.build_docs()
    undocumented = get_all_exported_names() - {
        "hypothesis.extra.numpy.BroadcastableShapes",
    }

    # `inventory` looks like:
    #   {
    #       "py:class": {
    #           "hypothesis.HealthCheck": (
    #               "Hypothesis",
    #               "6.129.4",
    #               "reference/api.html#hypothesis.HealthCheck",
    #               "-",
    #           ),
    #           ...
    #       },
    #       ...
    #   }
    inventory_path = (
        Path(hp.HYPOTHESIS_PYTHON) / "docs" / "_build" / "html" / "objects.inv"
    )
    with open(inventory_path, "rb") as f:
        inventory = InventoryFile.load(f, "", posixpath.join)

    for items in inventory.values():
        undocumented -= set(items.keys())
    assert not undocumented, f"undocumented strategies: {sorted(undocumented)}"
