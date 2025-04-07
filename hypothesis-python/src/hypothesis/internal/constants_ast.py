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
import sys
from ast import AST, NodeVisitor
from typing import TYPE_CHECKING, Union

from hypothesis.internal.escalation import is_hypothesis_file
from hypothesis.internal.scrutineer import _path_type

if TYPE_CHECKING:
    from typing import TypeAlias

ConstantT: "TypeAlias" = Union[int, float, bool, bytes, str]


class ConstantVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.constants: set[ConstantT] = set()

    def visit_JoinedStr(self, node):
        # dont recurse on JoinedStr, i.e. f strings. Constants that appear *only*
        # in f strings are unlikely to be helpful.
        return

    @classmethod
    def _unfold_constant(cls, value: object) -> set[ConstantT]:
        if isinstance(value, str) and (len(value) > 20 or value.isspace()):
            # discard long strings, which are likely to be docstrings.
            # TODO we should always ignore strings directly after a FunctionDef
            # node, regardless of length
            return set()
        if isinstance(value, (int, float, bool, bytes, str)):
            return {value}
        if isinstance(value, (tuple, frozenset)):
            return set.union(*[cls._unfold_constant(c) for c in value])
        return set()

    def visit_Constant(self, node):
        self.constants |= self._unfold_constant(node.value)
        self.generic_visit(node)


def constants_from_ast(tree: AST) -> set[ConstantT]:
    visitor = ConstantVisitor()
    visitor.visit(tree)
    return visitor.constants


def local_modules():
    modules = []
    for module in sys.modules.values():
        if not hasattr(module, "__file__"):
            continue
        if module.__file__ is None:
            continue

        # 0 means a local module
        if _path_type(module.__file__) != 0:
            continue

        modules.append(module)
    return modules


def local_constants():
    constants = set()
    for module in local_modules():
        if is_hypothesis_file(module.__file__):
            continue

        try:
            source = inspect.getsource(module)
            tree = ast.parse(source)
        except Exception:
            pass

        constants |= constants_from_ast(tree)

    return constants
