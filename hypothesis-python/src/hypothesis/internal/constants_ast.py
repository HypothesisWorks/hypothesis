# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import ast
import hashlib
import inspect
import math
import sys
from ast import Constant, Expr, NodeVisitor, UnaryOp, USub
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, AbstractSet, TypedDict, Union

import hypothesis
from hypothesis.configuration import storage_directory
from hypothesis.internal.escalation import is_hypothesis_file

if TYPE_CHECKING:
    from typing import TypeAlias

ConstantT: "TypeAlias" = Union[int, float, bytes, str]


class ConstantsT(TypedDict):
    integer: AbstractSet[int]
    float: AbstractSet[float]
    bytes: AbstractSet[bytes]
    string: AbstractSet[str]


class ConstantVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.constants: set[ConstantT] = set()

    def _add_constant(self, value: object) -> None:
        if isinstance(value, str) and (
            len(value) > 20 or value.isspace() or value == ""
        ):
            # discard long strings, which are unlikely to be useful.
            return
        if isinstance(value, bytes) and value == b"":
            return
        if isinstance(value, bool):
            return
        if isinstance(value, float) and math.isinf(value):
            # we already upweight inf.
            return
        if isinstance(value, int) and -100 < value < 100:
            # we already upweight small integers.
            return

        if isinstance(value, (int, float, bytes, str)):
            self.constants.add(value)
            return

        # I don't kow what case could go here, but am also not confident there
        # isn't one.
        return  # pragma: no cover

    def visit_UnaryOp(self, node: UnaryOp) -> None:
        # `a = -1` is actually a combination of a USub and the constant 1.
        if (
            isinstance(node.op, USub)
            and isinstance(node.operand, Constant)
            and isinstance(node.operand.value, (int, float))
            and not isinstance(node.operand.value, bool)
        ):
            self._add_constant(-node.operand.value)
            # don't recurse on this node to avoid adding the positive variant
            return

        self.generic_visit(node)

    def visit_Expr(self, node: Expr) -> None:
        if isinstance(node.value, Constant) and isinstance(node.value.value, str):
            return

        self.generic_visit(node)

    def visit_JoinedStr(self, node):
        # dont recurse on JoinedStr, i.e. f strings. Constants that appear *only*
        # in f strings are unlikely to be helpful.
        return

    def visit_Constant(self, node):
        self._add_constant(node.value)
        self.generic_visit(node)


def _constants_from_source(source: Union[str, bytes]) -> AbstractSet[ConstantT]:
    tree = ast.parse(source)
    visitor = ConstantVisitor()
    visitor.visit(tree)
    return visitor.constants


@lru_cache(4096)
def constants_from_module(module: ModuleType) -> AbstractSet[ConstantT]:
    try:
        module_file = inspect.getsourcefile(module)
        # use type: ignore because we know this might error
        source_bytes = Path(module_file).read_bytes()  # type: ignore
    except Exception:
        return set()

    source_hash = hashlib.sha1(source_bytes).hexdigest()[:16]
    cache_p = storage_directory("constants") / source_hash
    try:
        return _constants_from_source(cache_p.read_bytes())
    except Exception:
        # if the cached location doesn't exist, or it does exist but there was
        # a problem reading it, fall back to standard computation of the constants
        pass

    try:
        constants = _constants_from_source(source_bytes)
    except Exception:
        # A bunch of things can go wrong here.
        # * ast.parse may fail on the source code
        # * NodeVisitor may hit a RecursionError (see many related issues on
        #   e.g. libcst https://github.com/Instagram/LibCST/issues?q=recursion),
        #   or a MemoryError (`"[1, " * 200 + "]" * 200`)
        return set()

    try:
        cache_p.parent.mkdir(parents=True, exist_ok=True)
        cache_p.write_text(
            f"# file: {module_file}\n# hypothesis_version: {hypothesis.__version__}\n\n"
            # somewhat arbitrary sort order. The cache file doesn't *have* to be
            # stable... but it is aesthetically pleasing, and means we could rely
            # on it in the future!
            + str(sorted(constants, key=lambda v: (str(type(v)), v))),
            encoding="utf-8",
        )
    except Exception:  # pragma: no cover
        pass

    return constants


@lru_cache(4096)
def is_local_module_file(path: str) -> bool:
    from hypothesis.internal.scrutineer import ModuleLocation

    return (
        # Skip expensive path lookup for stdlib modules.
        # This will cause false negatives if a user names their module the
        # same as a stdlib module.
        #
        # sys.stdlib_module_names is new in 3.10
        not (sys.version_info >= (3, 10) and path in sys.stdlib_module_names)
        # A path containing site-packages is extremely likely to be
        # ModuleLocation.SITE_PACKAGES. Skip the expensive path lookup here.
        and "/site-packages/" not in path
        and ModuleLocation.from_path(path) is ModuleLocation.LOCAL
        # normally, hypothesis is a third-party library and is not returned
        # by local_modules. However, if it is installed as an editable package
        # with pip install -e, then we will pick up on it. Just hardcode an
        # ignore here.
        and not is_hypothesis_file(path)
        # avoid collecting constants from test files
        and not (
            "test" in (p := Path(path)).parts
            or "tests" in p.parts
            or p.stem.startswith("test_")
            or p.stem.endswith("_test")
        )
    )
