# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This file originates in the IPython project and is made use of under the
following licensing terms:

The IPython licensing terms
IPython is licensed under the terms of the Modified BSD License (also known as
New or Revised or 3-Clause BSD), as follows:

Copyright (c) 2008-2014, IPython Development Team
Copyright (c) 2001-2007, Fernando Perez <fernando.perez@colorado.edu>
Copyright (c) 2001, Janko Hauser <jhauser@zscout.de>
Copyright (c) 2001, Nathaniel Gray <n8gray@caltech.edu>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the name of the IPython Development Team nor the names of its
contributors may be used to endorse or promote products derived from this
software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import io
import re
import struct
import sys
import warnings
from collections import Counter, OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, Flag
from functools import partial

import attrs
import pytest

from hypothesis import given, strategies as st
from hypothesis.control import current_build_context
from hypothesis.internal.compat import PYPY
from hypothesis.internal.conjecture.floats import float_to_lex
from hypothesis.internal.floats import SIGNALING_NAN
from hypothesis.vendor import pretty


class MyList:
    def __init__(self, content):
        self.content = content

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("MyList(...)")
        else:
            with p.group(3, "MyList(", ")"):
                for i, child in enumerate(self.content):
                    if i:
                        p.text(",")
                        p.breakable()
                    else:
                        p.breakable("")
                    p.pretty(child)


class MyDict(dict):
    def _repr_pretty_(self, p, cycle):
        p.text("MyDict(...)")


class MyObj:
    def somemethod(self):
        pass


class Dummy1:
    def _repr_pretty_(self, p, cycle):
        p.text("Dummy1(...)")


class Dummy2:
    _repr_pretty_ = None

    def __repr__(self):
        return "Dummy2()"


class NoModule:
    pass


NoModule.__module__ = None


class Breaking:
    def _repr_pretty_(self, p, cycle):
        with p.group(4, "TG: ", ":"):
            p.text("Breaking(")
            p.break_()
            p.text(")")


class BreakingRepr:
    def __repr__(self):
        return "Breaking(\n)"


class BreakingReprParent:
    def _repr_pretty_(self, p, cycle):
        with p.group(4, "TG: ", ":"):
            p.pretty(BreakingRepr())


class BadRepr:
    def __repr__(self):
        return 1 / 0


def test_list():
    assert pretty.pretty([]) == "[]"
    assert pretty.pretty([1]) == "[1]"


def test_dict():
    assert pretty.pretty({}) == "{}"
    assert pretty.pretty({1: 1}) == "{1: 1}"
    assert pretty.pretty({1: 1, 0: 0}) == "{1: 1, 0: 0}"

    # Check that pretty-printing doesn't trigger a BytesWarning under `python -bb`
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", BytesWarning)
        x = {"": 0, b"": 0}
    assert pretty.pretty(x) == "{'': 0, b'': 0}"


def test_tuple():
    assert pretty.pretty(()) == "()"
    assert pretty.pretty((1,)) == "(1,)"
    assert pretty.pretty((1, 2)) == "(1, 2)"


class ReprDict(dict):
    def __repr__(self):
        return "hi"


def test_dict_with_custom_repr():
    assert pretty.pretty(ReprDict()) == "hi"


class ReprList(list):
    def __repr__(self):
        return "bye"


class ReprSet(set):
    def __repr__(self):
        return "cat"


def test_set_with_custom_repr():
    assert pretty.pretty(ReprSet()) == "cat"


def test_list_with_custom_repr():
    assert pretty.pretty(ReprList()) == "bye"


def test_indentation():
    """Test correct indentation in groups."""
    count = 40
    gotoutput = pretty.pretty(MyList(range(count)))
    expectedoutput = "MyList(\n" + ",\n".join(f"   {i}" for i in range(count)) + ")"

    assert gotoutput == expectedoutput


def test_dispatch():
    """Test correct dispatching: The _repr_pretty_ method for MyDict must be
    found before the registered printer for dict."""
    gotoutput = pretty.pretty(MyDict())
    expectedoutput = "MyDict(...)"

    assert gotoutput == expectedoutput


def test_callability_checking():
    """Test that the _repr_pretty_ method is tested for callability and skipped
    if not."""
    gotoutput = pretty.pretty(Dummy2())
    expectedoutput = "Dummy2()"

    assert gotoutput == expectedoutput


def test_sets():
    """Test that set and frozenset use Python 3 formatting."""
    objects = [
        set(),
        frozenset(),
        {1},
        frozenset([1]),
        {1, 2},
        frozenset([1, 2]),
        {-1, -2, -3},
    ]
    expected = [
        "set()",
        "frozenset()",
        "{1}",
        "frozenset({1})",
        "{1, 2}",
        "frozenset({1, 2})",
        "{-3, -2, -1}",
    ]
    for obj, expected_output in zip(objects, expected):
        got_output = pretty.pretty(obj)
        assert got_output == expected_output


def test_unsortable_set():
    xs = {1, 2, 3, "foo", "bar", "baz", object()}
    p = pretty.pretty(xs)
    for x in xs:
        assert pretty.pretty(x) in p


def test_unsortable_dict():
    xs = {k: 1 for k in [1, 2, 3, "foo", "bar", "baz", object()]}
    p = pretty.pretty(xs)
    for x in xs:
        assert pretty.pretty(x) in p


def test_pprint_nomod():
    """Test that pprint works for classes with no __module__."""
    output = pretty.pretty(NoModule)
    assert output == "NoModule"


def test_pprint_break():
    """Test that p.break_ produces expected output."""
    output = pretty.pretty(Breaking())
    expected = "TG: Breaking(\n    ):"
    assert output == expected


def test_pprint_break_repr():
    """Test that p.break_ is used in repr."""
    output = pretty.pretty(BreakingReprParent())
    expected = "TG: Breaking(\n    ):"
    assert output == expected


def test_bad_repr():
    """Don't catch bad repr errors."""
    with pytest.raises(ZeroDivisionError):
        pretty.pretty(BadRepr())


class BadException(Exception):
    def __str__(self):
        return -1  # noqa


class ReallyBadRepr:
    __module__ = 1

    @property
    def __class__(self):
        raise ValueError("I am horrible")

    def __repr__(self):
        raise BadException


def test_really_bad_repr():
    with pytest.raises(BadException):
        pretty.pretty(ReallyBadRepr())


class SA:
    pass


class SB(SA):
    pass


try:
    super(SA).__self__

    def test_super_repr():
        output = pretty.pretty(super(SA))
        assert "SA" in output

        sb = SB()
        output = pretty.pretty(super(SA, sb))
        assert "SA" in output

except AttributeError:

    def test_super_repr():
        pretty.pretty(super(SA))
        sb = SB()
        pretty.pretty(super(SA, sb))


def test_long_list():
    lis = list(range(10000))
    p = pretty.pretty(lis)
    last2 = p.rsplit("\n", 2)[-2:]
    assert last2 == [" 999,", " ...]"]


def test_long_set():
    s = set(range(10000))
    p = pretty.pretty(s)
    last2 = p.rsplit("\n", 2)[-2:]
    assert last2 == [" 999,", " ...}"]


def test_long_tuple():
    tup = tuple(range(10000))
    p = pretty.pretty(tup)
    last2 = p.rsplit("\n", 2)[-2:]
    assert last2 == [" 999,", " ...)"]


def test_long_dict():
    d = {n: n for n in range(10000)}
    p = pretty.pretty(d)
    last2 = p.rsplit("\n", 2)[-2:]
    assert last2 == [" 999: 999,", " ...}"]


def test_unbound_method():
    assert pretty.pretty(MyObj.somemethod) == "somemethod"


class MetaClass(type):
    def __new__(metacls, name):
        return type.__new__(metacls, name, (object,), {"name": name})

    def __repr__(cls):
        return f"[CUSTOM REPR FOR CLASS {cls.name}]"


ClassWithMeta = MetaClass("ClassWithMeta")


def test_metaclass_repr():
    output = pretty.pretty(ClassWithMeta)
    assert output == "[CUSTOM REPR FOR CLASS ClassWithMeta]"


def test_unicode_repr():
    u = "üniçodé"

    class C:
        def __repr__(self):
            return u

    c = C()
    p = pretty.pretty(c)
    assert p == u
    p = pretty.pretty([c])
    assert p == f"[{u}]"


def test_basic_class():
    def type_pprint_wrapper(obj, p, cycle):
        if obj is MyObj:
            type_pprint_wrapper.called = True
        return pretty._type_pprint(obj, p, cycle)

    type_pprint_wrapper.called = False

    printer = pretty.RepresentationPrinter()
    printer.type_pprinters[type] = type_pprint_wrapper
    printer.pretty(MyObj)
    output = printer.getvalue()

    assert output == f"{__name__}.MyObj"
    assert type_pprint_wrapper.called


def test_collections_defaultdict():
    # Create defaultdicts with cycles
    a = defaultdict()
    a.default_factory = a
    b = defaultdict(list)
    b["key"] = b

    # Dictionary order cannot be relied on, test against single keys.
    cases = [
        (defaultdict(list), "defaultdict(list, {})"),
        (
            defaultdict(list, {"key": "-" * 50}),
            "defaultdict(list,\n"
            "            {'key': '-----------------------------------------"
            "---------'})",
        ),
        (a, "defaultdict(defaultdict(...), {})"),
        (b, "defaultdict(list, {'key': defaultdict(...)})"),
    ]
    for obj, expected in cases:
        assert pretty.pretty(obj) == expected


@pytest.mark.skipif(PYPY, reason="slightly different on PyPy3")
def test_collections_ordereddict():
    # Create OrderedDict with cycle
    a = OrderedDict()
    a["key"] = a

    cases = [
        (OrderedDict(), "OrderedDict()"),
        (
            OrderedDict((i, i) for i in range(1000, 1010)),
            "OrderedDict([(1000, 1000),\n"
            "             (1001, 1001),\n"
            "             (1002, 1002),\n"
            "             (1003, 1003),\n"
            "             (1004, 1004),\n"
            "             (1005, 1005),\n"
            "             (1006, 1006),\n"
            "             (1007, 1007),\n"
            "             (1008, 1008),\n"
            "             (1009, 1009)])",
        ),
        (a, "OrderedDict([('key', OrderedDict(...))])"),
    ]
    for obj, expected in cases:
        assert pretty.pretty(obj) == expected


def test_collections_deque():
    # Create deque with cycle
    a = deque()
    a.append(a)

    cases = [
        (deque(), "deque([])"),
        (deque([1, 2, 3]), "deque([1, 2, 3])"),
        (
            deque(i for i in range(1000, 1020)),
            "deque([1000,\n"
            "       1001,\n"
            "       1002,\n"
            "       1003,\n"
            "       1004,\n"
            "       1005,\n"
            "       1006,\n"
            "       1007,\n"
            "       1008,\n"
            "       1009,\n"
            "       1010,\n"
            "       1011,\n"
            "       1012,\n"
            "       1013,\n"
            "       1014,\n"
            "       1015,\n"
            "       1016,\n"
            "       1017,\n"
            "       1018,\n"
            "       1019])",
        ),
        (a, "deque([deque(...)])"),
    ]
    for obj, expected in cases:
        assert pretty.pretty(obj) == expected


def test_collections_counter():
    class MyCounter(Counter):
        pass

    cases = [
        (Counter(), "Counter()"),
        (Counter(a=1), "Counter({'a': 1})"),
        (MyCounter(a=1), "MyCounter({'a': 1})"),
    ]
    for obj, expected in cases:
        assert pretty.pretty(obj) == expected


def test_cyclic_list():
    x = []
    x.append(x)
    assert pretty.pretty(x) == "[[...]]"


def test_cyclic_dequeue():
    x = deque()
    x.append(x)
    assert pretty.pretty(x) == "deque([deque(...)])"


class HashItAnyway:
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return isinstance(other, HashItAnyway) and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def _repr_pretty_(self, pretty, cycle):
        pretty.pretty(self.value)


def test_cyclic_counter():
    c = Counter()
    k = HashItAnyway(c)
    c[k] = 1
    assert pretty.pretty(c) == "Counter({Counter(...): 1})"


def test_cyclic_dict():
    x = {}
    k = HashItAnyway(x)
    x[k] = x
    assert pretty.pretty(x) == "{{...}: {...}}"


def test_cyclic_set():
    x = set()
    x.add(HashItAnyway(x))
    assert pretty.pretty(x) == "{{...}}"


class BigList(list):
    def _repr_pretty_(self, printer, cycle):
        if cycle:
            return "[...]"
        else:
            with printer.group(open="[", close="]"):
                with printer.indent(5):
                    for v in self:
                        printer.pretty(v)
                        printer.breakable(",")


def test_print_with_indent():
    pretty.pretty(BigList([1, 2, 3]))


class MyException(Exception):
    pass


def test_exception():
    assert pretty.pretty(ValueError("hi")) == "ValueError('hi')"
    assert pretty.pretty(ValueError("hi", "there")) == "ValueError('hi', 'there')"
    assert "test_pretty." in pretty.pretty(MyException())


def test_re_evals():
    for r in [
        re.compile(r"hi"),
        re.compile(r"b\nc", re.MULTILINE),
        re.compile(rb"hi", 0),
        re.compile("foo", re.MULTILINE | re.UNICODE),
    ]:
        r2 = eval(pretty.pretty(r), globals())
        assert r.pattern == r2.pattern
        assert r.flags == r2.flags


def test_print_builtin_function():
    assert pretty.pretty(abs) == "abs"


def test_pretty_function():
    assert pretty.pretty(test_pretty_function) == "test_pretty_function"


def test_breakable_at_group_boundary():
    assert "\n" in pretty.pretty([[], "0" * 80])


@pytest.mark.parametrize(
    "obj, rep",
    [
        (float("nan"), "nan"),
        (-float("nan"), "-nan"),
        (SIGNALING_NAN, "struct.unpack('d', struct.pack('Q', 0x7ff8000000000001))[0]"),
        (-SIGNALING_NAN, "struct.unpack('d', struct.pack('Q', 0xfff8000000000001))[0]"),
    ],
)
def test_nan_reprs(obj, rep):
    assert pretty.pretty(obj) == rep
    assert float_to_lex(obj) == float_to_lex(
        eval(rep, {"struct": struct, "nan": float("nan")})
    )


def _repr_call(*args, **kwargs):
    p = pretty.RepresentationPrinter()
    p.repr_call(*args, **kwargs)
    return p.getvalue()


@pytest.mark.parametrize("func_name", ["f", "lambda: ...", "lambda *args: ..."])
def test_repr_call(func_name):
    fn = f"({func_name})" if func_name.startswith(("lambda:", "lambda ")) else func_name
    aas = "a" * 100
    assert _repr_call(func_name, (1, 2), {}) == f"{fn}(1, 2)"
    assert _repr_call(func_name, (aas,), {}) == f"{fn}(\n    {aas!r},\n)"
    assert _repr_call(func_name, (), {"a": 1, "b": 2}) == f"{fn}(a=1, b=2)"
    assert _repr_call(func_name, (), {"x": aas}) == f"{fn}(\n    x={aas!r},\n)"


class AnEnum(Enum):
    SOME_MEMBER = 1


class Options(Flag):
    A = 1
    B = 2
    C = 4


class EvilReprOptions(Flag):
    A = 1
    B = 2

    def __repr__(self):
        return "can't parse this nonsense"


class LyingReprOptions(Flag):
    A = 1
    B = 2

    def __repr__(self):
        return "LyingReprOptions.A|B|C"


@pytest.mark.parametrize(
    "rep",
    [
        "AnEnum.SOME_MEMBER",
        "Options.A",
        "Options.A | Options.B",
        "Options.A | Options.B | Options.C",
        "Options(0)",
        "EvilReprOptions.A",
        "LyingReprOptions.A",
        "EvilReprOptions.A | EvilReprOptions.B",
        "LyingReprOptions.A | LyingReprOptions.B",
    ],
)
def test_pretty_prints_enums_as_code(rep):
    assert pretty.pretty(eval(rep)) == rep


class Obj:
    def _repr_pretty_(self, p, cycle):
        """Exercise the IPython callback interface."""
        assert not cycle
        with p.indent(2):
            p.text("abc,")
            p.breakable(" ")
            p.break_()
        p.begin_group(8, "<")
        p.end_group(8, ">")


def test_supports_ipython_callback():
    assert pretty.pretty(Obj()) == "abc, \n  <>"


def test_pretty_partial_with_cycle():
    ls = []
    p = partial(bool, ls)
    assert pretty.pretty(p) == "functools.partial(bool, [])"
    ls.append(p)
    assert pretty.pretty(p) == "functools.partial(bool, [functools.partial(bool, ...)])"


class InvalidSyntaxRepr:
    def __init__(self, val=None) -> None:
        self.val = val

    def __repr__(self):
        return "invalid syntax"


class ValidSyntaxRepr:
    def __init__(self, val=None) -> None:
        self.val = val

    def __repr__(self):
        return "ValidSyntaxRepr(...)"


@given(st.data())
def test_pprint_with_call_or_repr_as_call(data):
    # mapped pprint repr only triggers for failing examples - which makes an
    # end to end test given hypothesis difficult. fake our way around it.
    current_build_context().is_final = True

    x = data.draw(st.none().map(InvalidSyntaxRepr))
    p = pretty.RepresentationPrinter(context=current_build_context())
    p.pretty(x)
    assert p.getvalue() == "InvalidSyntaxRepr(None)"


@given(st.just(InvalidSyntaxRepr()).map(ValidSyntaxRepr))
def test_pprint_with_call_or_repr_as_repr(x):
    p = pretty.RepresentationPrinter(context=current_build_context())
    p.pretty(x)
    assert p.getvalue() == "ValidSyntaxRepr(...)"


@given(st.data())
def test_pprint_map_with_cycle(data):
    current_build_context().is_final = True
    x = data.draw(st.just(ValidSyntaxRepr()).map(lambda x: x))

    p = pretty.RepresentationPrinter(context=current_build_context())
    p.pretty(x)
    assert p.getvalue() == "ValidSyntaxRepr(...)"


def test_pprint_large_integers():
    p = pretty.RepresentationPrinter()
    p.pretty(1234567890)
    assert p.getvalue() == "1_234_567_890"


def test_pprint_extremely_large_integers():
    x = 10**5000  # repr fails with ddos error
    p = pretty.RepresentationPrinter()
    p.pretty(x)
    got = p.getvalue()
    assert got == f"{x:#_x}"  # hexadecimal with underscores
    assert eval(got) == x


class ReprDetector:
    def _repr_pretty_(self, p, cycle):
        """Exercise the IPython callback interface."""
        p.text("GOOD")

    def __repr__(self):
        return "BAD"


@dataclass
class SomeDataClass:
    x: object


def test_pretty_prints_data_classes():
    assert pretty.pretty(SomeDataClass(ReprDetector())) == "SomeDataClass(x=GOOD)"


@attrs.define
class SomeAttrsClass:
    x: ReprDetector


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
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


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
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


def test_handles_cycles_in_dataclass():
    x = SomeDataClass(x=1)
    x.x = x

    assert pretty.pretty(x) == "SomeDataClass(x=SomeDataClass(...))"


@dataclass
class DataClassWithNoInitField:
    x: int
    y: int = field(init=False)


def test_does_not_include_no_init_fields_in_dataclass_printing():
    record = DataClassWithNoInitField(x=1)
    assert pretty.pretty(record) == "DataClassWithNoInitField(x=1)"
    record.y = 1
    assert pretty.pretty(record) == "DataClassWithNoInitField(x=1)"


@attrs.define
class AttrsClassWithNoInitField:
    x: int
    y: int = attrs.field(init=False)


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
def test_does_not_include_no_init_fields_in_attrs_printing():
    record = AttrsClassWithNoInitField(x=1)
    assert pretty.pretty(record) == "AttrsClassWithNoInitField(x=1)"
    record.y = 1
    assert pretty.pretty(record) == "AttrsClassWithNoInitField(x=1)"


class Namespace:
    @dataclass
    class DC:
        x: int

    @attrs.define
    class A:
        x: int

    class E(Enum):
        A = 1


NAMESPACED_VALUES = [
    Namespace.DC(x=1),
    Namespace.A(x=1),
    Namespace.E.A,
]


@pytest.mark.parametrize("obj", NAMESPACED_VALUES, ids=map(repr, NAMESPACED_VALUES))
def test_includes_namespace_classes_in_pretty(obj):
    assert pretty.pretty(obj).startswith("Namespace.")


class Banana:
    def _repr_pretty_(self, p, cycle):
        p.text("I am a banana")


@dataclass
class InheritsPretty(Banana):
    x: int
    y: int


def test_uses_defined_pretty_printing_method():
    assert pretty.pretty(InheritsPretty(x=1, y=2)) == pretty.pretty(Banana())


def test_prefers_singleton_printing_to_repr_pretty():
    out = io.StringIO()
    printer = pretty.RepresentationPrinter(out)
    banana = Banana()
    printer.singleton_pprinters[id(banana)] = lambda obj, p, cycle: p.text(
        "Actually a fish"
    )
    printer.pretty(banana)
    assert "Actually a fish" in out.getvalue()
