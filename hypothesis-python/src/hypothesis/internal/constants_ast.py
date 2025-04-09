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
import inspect
import math
import sys
from ast import AST, Constant, Expr, NodeVisitor, UnaryOp, USub
from functools import lru_cache
from types import ModuleType
from typing import TYPE_CHECKING, Optional, Union

from hypothesis.internal.escalation import is_hypothesis_file
from hypothesis.internal.scrutineer import ModuleLocation

if TYPE_CHECKING:
    from typing import TypeAlias

ConstantT: "TypeAlias" = Union[int, float, bytes, str]


class ConstantVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.constants: set[ConstantT] = set()

    def _add_constant(self, constant: object) -> None:
        self.constants |= self._unfold_constant(constant)

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

    @classmethod
    def _unfold_constant(cls, value: object) -> set[ConstantT]:
        if isinstance(value, str) and (
            len(value) > 20 or value.isspace() or value == ""
        ):
            # discard long strings, which are unlikely to be useful.
            return set()
        if isinstance(value, bool):
            return set()
        if isinstance(value, float) and math.isinf(value):
            # we already upweight inf.
            return set()
        if isinstance(value, (int, float, bytes, str)):
            return {value}
        # I don't kow what case could go here, but am also not confident there
        # isn't one.
        return set()  # pragma: no cover

    def visit_Constant(self, node):
        self._add_constant(node.value)
        self.generic_visit(node)


@lru_cache(1024)
def constants_from_ast(tree: AST) -> set[ConstantT]:
    visitor = ConstantVisitor()
    visitor.visit(tree)
    return visitor.constants


@lru_cache(1024)
def _module_ast(module: ModuleType) -> Optional[AST]:
    try:
        source = inspect.getsource(module)
        tree = ast.parse(source)
    except Exception:
        return None

    return tree


def local_modules() -> tuple[ModuleType, ...]:
    modules = []
    for module in sys.modules.values():
        if (
            not hasattr(module, "__file__")
            or module.__file__ is None
            # Skip expensive path lookup for stdlib modules.
            # This will cause false negatives if a user names their module the
            # same as a stdlib module.
            #
            # sys.stdlib_module_names is new in 3.10
            or (
                sys.version_info >= (3, 10)
                and module.__name__ in sys.stdlib_module_names
            )
            or ModuleLocation.from_path(module.__file__) is not ModuleLocation.LOCAL
        ):
            continue

        modules.append(module)
    return tuple(modules)


def local_constants():
    constants = set()
    for module in local_modules():
        # normally, hypothesis is a third-party library and is not returned
        # by local_modules. However, if it is installed as an editable package
        # with pip install -e, then we will pick up on it. Just hardcode an
        # ignore here.

        # this is actually covered by test_constants_from_running_file, but
        # not in the same process.
        if is_hypothesis_file(module.__file__):  # pragma: no cover
            continue

        tree = _module_ast(module)
        if tree is None:  # pragma: no cover
            continue
        constants |= constants_from_ast(tree)

    return constants
