# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import attrs

from hypothesis.vendor import pretty


class ReprDetector:
    def _repr_pretty_(self, p, cycle):
        """Exercise the IPython callback interface."""
        p.text("GOOD")

    def __repr__(self):
        return "BAD"


@attrs.define
class SomeAttrsClass:
    x: ReprDetector


def test_pretty_prints_attrs_classes():
    assert pretty.pretty(SomeAttrsClass(ReprDetector())) == "SomeAttrsClass(x=GOOD)"


@attrs.define
class SomeAttrsClassWithCustomPretty:
    def _repr_pretty_(self, p, cycle):
        """Exercise the IPython callback interface."""
        p.text("I am a banana")


def test_custom_pretty_print_method_overrides_field_printing():
    assert pretty.pretty(SomeAttrsClassWithCustomPretty()) == "I am a banana"


@attrs.define
class SomeAttrsClassWithLotsOfFields:
    a: int
    b: int
    c: int
    d: int
    e: int
    f: int
    g: int
    h: int
    i: int
    j: int
    k: int
    l: int
    m: int
    n: int
    o: int
    p: int
    q: int
    r: int
    s: int


def test_will_line_break_between_fields():
    obj = SomeAttrsClassWithLotsOfFields(
        **{
            at.name: 12345678900000000000000001
            for at in SomeAttrsClassWithLotsOfFields.__attrs_attrs__
        }
    )
    assert "\n" in pretty.pretty(obj)


@attrs.define
class SomeDataClassWithNoFields: ...


def test_prints_empty_dataclass_correctly():
    assert pretty.pretty(SomeDataClassWithNoFields()) == "SomeDataClassWithNoFields()"


@attrs.define
class AttrsClassWithNoInitField:
    x: int
    y: int = attrs.field(init=False)


def test_does_not_include_no_init_fields_in_attrs_printing():
    record = AttrsClassWithNoInitField(x=1)
    assert pretty.pretty(record) == "AttrsClassWithNoInitField(x=1)"
    record.y = 1
    assert pretty.pretty(record) == "AttrsClassWithNoInitField(x=1)"


class Namespace:
    @attrs.define
    class A:
        x: int


def test_includes_namespace_classes_in_pretty():
    obj = Namespace.A(x=1)
    assert pretty.pretty(obj) == "Namespace.A(x=1)"
