# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for inverting string-building packs in MappedStrategy._invert.

Kept separate from test_invert.py, which covers the per-strategy _invert
implementations: everything here exercises the source-analysis machinery in
hypothesis.internal.invertstring through .map().
"""

import functools
import operator

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import CannotInvert
from hypothesis.internal.invertstring import preimage_candidates

from tests.cover.test_invert import assert_roundtrip, check_roundtrip_many

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)

GLOBAL_PREFIX = "gl-"
FMT_AUTO = "id-{}"
FMT_NAMED = "id-{name}"
FMT_MANUAL = "{0}:{1}"
FMT_TRAILING = "{}!"
FMT_SPEC = "{:>5}"
FMT_BROKEN = "id-{"
FMT_OUT_OF_RANGE = "{1}"
# %-templates for explicit-tuple right-hand sides, which shed would
# otherwise rewrite into f-strings
PCT_SINGLE = "%s"
PCT_PAIR = "%s+%s"
PCT_PAIR_D = "%s=%d"
PCT_TRAILING = "%s>50%"


def make_closure_pack():
    prefix = "id-"
    return lambda s: prefix + s


def named_pack(s):
    return "id-" + s


def docstring_pack(s):
    """Prefix the argument."""
    return "id-" + s


def multi_statement_pack(s):
    prefix = "id-"
    return prefix + s


async def async_pack(s):
    return "id-" + s


# The bodies are unique to this file: a code-identical lambda elsewhere
# would share a lambda-description cache entry, and then the (correct!)
# recovered source would make these invertible after all.
_exec_namespace = {}
exec("def exec_pack(s): return 'exec-' + s", _exec_namespace)
EXEC_PACK = _exec_namespace["exec_pack"]
EVAL_PACK = eval('lambda s: "eval-" + s')


class _RaisingStr(str):
    def __add__(self, other):
        raise RuntimeError("boom")


class _SneakyStr(str):
    def __add__(self, other):
        return "not what the source says"


RAISING_PREFIX = _RaisingStr("id-")
SNEAKY_PREFIX = _SneakyStr("id-")


@pytest.mark.parametrize(
    "strategy,value",
    [
        # constant concatenation
        (st.text().map(lambda s: "id-" + s), "id-abc"),
        (st.text().map(lambda s: s + ".txt"), "hello.txt"),
        (st.text().map(lambda s: "<" + s + ">"), "<x>"),
        (st.text().map(lambda s: GLOBAL_PREFIX + s), "gl-xy"),
        (st.text().map(make_closure_pack()), "id-xy"),
        (st.text().map(named_pack), "id-xy"),
        (st.text().map(docstring_pack), "id-xy"),
        # str() and sourceless builtins
        (st.integers().map(str), "17"),
        (st.integers().map(str), "-3"),
        (st.floats().map(str), "1.5"),
        (st.booleans().map(str), "True"),
        (st.none().map(str), "None"),
        (st.integers().map(lambda n: "n" + str(n)), "n17"),
        # f-strings
        (st.text().map(lambda s: f"id-{s}"), "id-abc"),
        (st.integers().map(lambda n: f"n={n}!"), "n=17!"),
        (st.text().map(lambda s: f"{s!s}?"), "what?"),
        (st.tuples(st.text(), st.integers()).map(lambda t: f"{t[0]}={t[1]}"), "k=3"),
        (st.text(min_size=1).map(lambda s: f"{s}{s}"), "abab"),
        # str.format, positional and named.  The templates live in globals
        # because shed would rewrite literal-string .format calls into
        # f-strings, and we want to cover the .format() analysis too.
        (st.text().map(lambda s: FMT_AUTO.format(s)), "id-z"),
        (st.text().map(lambda s: FMT_NAMED.format(name=s)), "id-z"),
        (st.text().map("id-{}".format), "id-z"),
        (st.text().map("{0}~{0}".format), "x~x"),
        (
            st.tuples(st.integers(), st.text()).map(
                lambda t: FMT_MANUAL.format(t[0], t[1])
            ),
            "7:x",
        ),
        (st.text().map(lambda s: FMT_TRAILING.format(s)), "z!"),
        # %-formatting
        (st.text().map(lambda s: "id-%s" % s), "id-q"),  # noqa: UP031
        (st.integers().map(lambda n: "%d apples" % n), "3 apples"),  # noqa: UP031
        (st.integers().map(lambda n: "100%% of %d" % n), "100% of 9"),  # noqa: UP031
        (st.tuples(st.text(), st.integers()).map(lambda t: PCT_PAIR_D % t), "ab=3"),
        # case operations
        (st.text().map(str.upper), "ABC"),
        (st.text().map(lambda s: s.lower()), "abc"),
        (st.text().map(lambda s: s.title()), "Abc Def"),
        (st.text().map(lambda s: s.capitalize()), "Abc"),
        (st.text().map(lambda s: s.swapcase()), "aBC"),
        (st.text().map(lambda s: s.casefold()), "abc"),
        # strip family (fixed points only)
        (st.text().map(str.strip), "abc"),
        (st.text().map(lambda s: s.strip()), "a b"),
        (st.text().map(lambda s: s.lstrip("_")), "abc_"),
        (st.text().map(lambda s: s.rstrip("_")), "_abc"),
        # replace
        (st.text().map(lambda s: s.replace("a", "b")), "bbc"),
        (st.text().map(lambda s: s.replace("a", "")), "xyz"),
        # join
        (st.lists(st.text()).map(",".join), "a,b"),
        (st.lists(st.text()).map("".join), "ab"),
        (st.lists(st.text()).map(lambda ls: "-".join(ls)), "a-b-c"),
        (st.tuples(st.text(), st.text()).map(lambda t: "/".join(t)), "a/b"),
        # repetition
        (st.text().map(lambda s: s * 3), "ababab"),
        (st.text().map(lambda s: 2 * s), "xyxy"),
        (st.integers(0, 100).map(lambda n: "x" * n), "xxx"),
        # zfill / removeprefix / removesuffix
        (st.text(alphabet="123456789", min_size=1).map(lambda s: s.zfill(5)), "00042"),
        (st.text().map(lambda s: s.zfill(3)), "0ab"),
        (st.text().map(lambda s: s.removeprefix("id-")), "abc"),
        (st.text().map(lambda s: s.removesuffix(".txt")), "abc"),
        # chains of operations
        (st.text().map(lambda s: ("id-" + s).upper()), "ID-ABC"),
        (st.integers().map(lambda n: ("n=" + str(n)).replace("=", ":")), "n:5"),
        (st.text().map(lambda s: f"{s}!".upper()), "ABC!"),
        (st.text().map(lambda s: ("[" + s.strip("_") + "]").lower()), "[ab]"),
        # multi-argument packs via tuple subscripts
        (st.tuples(st.text(), st.integers()).map(lambda t: t[0] + str(t[1])), "ab3"),
        (
            st.tuples(st.text(), st.text(), st.text()).map(
                lambda t: t[0] + "." + t[1] + "." + t[2]
            ),
            "a.b.c",
        ),
        # ... and over lists
        (
            st.lists(st.text(), min_size=2, max_size=2).map(lambda ls: ls[0] + ls[1]),
            "ab",
        ),
    ],
)
def test_roundtrip_explicit(strategy, value):
    assert_roundtrip(strategy, value)


@pytest.mark.parametrize(
    "strategy,value,expected",
    [
        (st.text().map(lambda s: "id-" + s), "id-abc", ("abc",)),
        (st.integers().map(str), "17", (17,)),
        (st.integers().map(lambda n: f"n={n}"), "n=5", (5,)),
        (st.text().map(lambda s: ("id-" + s).upper()), "ID-AB", ("ab",)),
        (st.lists(st.text()).map("-".join), "a-b", (True, "a", True, "b", False)),
        (
            st.tuples(st.text(), st.integers()).map(lambda t: f"{t[0]}={t[1]}"),
            "k=3",
            ("k", 3),
        ),
    ],
)
def test_produces_expected_choice_sequence(strategy, value, expected):
    assert strategy._invert(value) == expected


@given(st.data())
def test_prefix_map_roundtrips(data):
    check_roundtrip_many(st.text().map(lambda s: "id-" + s), data)


@given(st.data())
def test_fstring_over_integers_roundtrips(data):
    check_roundtrip_many(st.integers().map(lambda n: f"n={n}!"), data)


@given(st.data())
def test_case_chain_roundtrips(data):
    strategy = st.text(alphabet="abcxyz").map(lambda s: ("id-" + s).upper())
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_join_roundtrips(data):
    check_roundtrip_many(st.lists(st.text()).map(",".join), data)


@given(st.data())
def test_multihole_tuple_pack_roundtrips(data):
    strategy = st.tuples(st.text(), st.integers()).map(lambda t: f"{t[0]}={t[1]}")
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_doubled_interpolation_roundtrips(data):
    check_roundtrip_many(st.text().map(lambda s: f"{s}{s}"), data)


@given(st.data())
def test_zfill_roundtrips(data):
    strategy = st.text(alphabet="123456789", min_size=1).map(lambda s: s.zfill(4))
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_replace_roundtrips(data):
    check_roundtrip_many(
        st.text(alphabet="ab-_").map(lambda s: s.replace("-", "_")), data
    )


def test_ambiguous_split_roundtrips():
    # "a-b-c" could split as ("a", "b-c") or ("a-b", "c"); either is fine,
    # since replay verification only requires that f(candidate) == value.
    strategy = st.tuples(st.text(), st.text()).map(lambda t: f"{t[0]}-{t[1]}")
    assert_roundtrip(strategy, "a-b-c")


def test_ambiguous_unreplace_roundtrips():
    # every "b" in the value may or may not have been an "a" before the
    # replace; any verifying candidate is acceptable
    strategy = st.text(alphabet="ab").map(lambda s: s.replace("a", "b"))
    assert_roundtrip(strategy, "bbb")


def test_candidate_enumeration_is_bounded():
    # two adjacent holes admit len(value)+1 splits; enumeration stops at 32
    candidates = list(preimage_candidates(lambda t: t[0] + t[1], "x" * 100))
    assert 0 < len(candidates) <= 32


@pytest.mark.parametrize(
    "strategy,value",
    [
        # unrecognized expressions
        (st.text().map(lambda s: s[::-1]), "abc"),
        (st.text().map(lambda s: s.encode()), b"abc"),
        (st.integers().map(lambda x: x + 1), 5),
        (st.integers().map(lambda x: -x), 5),
        # more than four holes in one template
        (
            st.tuples(*[st.text()] * 5).map(lambda t: t[0] + t[1] + t[2] + t[3] + t[4]),
            "abcde",
        ),
        # source unavailable or unusable
        (st.text().map(functools.partial(operator.add, "id-")), "id-x"),
        (st.text().map(len), 3),
        (st.text().map(EXEC_PACK), "exec-x"),
        (st.text().map(EVAL_PACK), "eval-x"),
        (st.text().map(async_pack), "id-x"),
        (st.text().map(multi_statement_pack), "id-x"),
        # a constant-only body tells us nothing about the argument
        (st.text().map(lambda s: "k"), "k"),
        # no candidate verifies
        (st.text().map(lambda s: "id-" + s), "nope"),
        (st.text().map(lambda s: s.strip("a")), "aXa"),
        (st.integers().map(lambda n: "%d" % n), "xx"),  # noqa: UP031
        # non-string values
        (st.text().map(lambda s: "id-" + s), 42),
        (st.text().map(lambda s: "id-" + s), None),
        # format specs and conversions we cannot invert
        (st.integers().map(lambda n: f"{n:03d}"), "007"),
        (st.integers().map(lambda n: f"{n:>5}"), "    7"),
        (st.text().map(lambda s: f"{s!r}"), "'x'"),
        (st.integers().map(lambda n: FMT_SPEC.format(n)), "    7"),
        (st.text().map(lambda s: FMT_BROKEN.format(s)), "id-x"),
        (st.text().map(lambda s: FMT_OUT_OF_RANGE.format(s)), "x"),
        (st.text().map(lambda s: FMT_NAMED.format(other=s)), "id-x"),
        (st.floats().map(lambda x: "%.2f" % x), "0.25"),  # noqa: UP031
        # the pack raises, or returns something else, when called on our
        # candidate: source analysis diverges from runtime behaviour, and
        # verification catches it
        (st.text().map(lambda s: RAISING_PREFIX + s), "id-x"),
        (st.text().map(lambda s: SNEAKY_PREFIX + s), "id-x"),
    ],
)
def test_uninvertible_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


def test_shadowed_str_is_not_assumed_to_be_the_builtin():
    def fake_str(x):
        return "shadowed"

    def make():
        str = fake_str
        return lambda n: "v" + str(n)

    with pytest.raises(CannotInvert):
        st.integers().map(make())._invert("v5")


# Direct unit tests of preimage_candidates, mostly for edge cases in which
# no (or only trivial) candidates should be produced.  Candidates from this
# function are unverified, so exact assertions here are about enumeration,
# not soundness.


def pc(fn, value):
    return list(preimage_candidates(fn, value))


def test_str_parse_candidates():
    assert pc(str, "17") == ["17", 17]
    assert pc(str, "1.5") == ["1.5", 1.5]
    assert pc(str, "True") == ["True", True]
    assert pc(str, "None") == ["None", None]
    assert pc(str, "007") == ["007"]


def test_constant_subexpressions_resolve():
    # a fully-constant tuple argument to join, and a constant interpolation
    assert "x|" in pc(lambda s: s + "|".join(("a", "b")), "x|a|b")  # noqa: FLY002
    assert pc(lambda s: f"{s}{GLOBAL_PREFIX}", "xgl-") == ["x"]
    # ...but a tuple containing the argument is beyond us (for now)
    assert pc(lambda t: "-".join((t[0], "x")), "a-x") == []


def test_replace_edge_cases():
    # replacing old with itself, or with nothing, only inverts as identity
    assert pc(lambda s: s.replace("a", "a"), "aba") == ["aba"]
    assert pc(lambda s: s.replace("", "z"), "b") == []
    # partial un-replacements are enumerated too
    assert set(pc(lambda s: s.replace("a", "b"), "bb")) == {"aa", "bb", "ab", "ba"}


def test_repetition_edge_cases():
    assert pc(lambda s: s * 3, "xx") == []  # length not divisible
    assert pc(lambda s: s * 3, "xyz") == []  # not a repetition
    assert pc(lambda n: "x" * n, "yyy") == []  # not made of the constant


def test_method_argument_guards():
    # keyword arguments, unresolvable or wrongly-typed constant arguments
    assert pc(lambda s: s.replace("a", "b", count=1), "x") == []
    assert pc(lambda s: s.replace(1, "b"), "x") == []
    assert pc(lambda s: s.strip(chr(97)), "x") == []
    assert pc(lambda s: s.strip(5), "x") == []
    assert pc(lambda s: s.removeprefix(5), "x") == []
    assert pc(lambda s: s.join("ab"), "axb") == []  # non-constant separator


def test_percent_template_guards():
    # the right-hand side must be a tuple of the right size, or a lone name
    assert pc(lambda t: PCT_PAIR % list(t), "a-b") == []
    assert pc(lambda t: PCT_SINGLE % (t[0], t[1]), "a") == []
    assert ("a", "b") in pc(lambda t: PCT_PAIR % (t[0], t[1]), "a+b")


def test_format_star_kwargs_are_rejected():
    assert pc(lambda s: FMT_NAMED.format(**{"name": s}), "id-x") == []  # noqa: PIE804


def test_more_unrecognized_expressions():
    assert pc(lambda s: s + 5, "x5") == []  # non-string constant in concat
    assert pc(lambda s: "a" + f"{s!r}", "a'x'") == []  # !r nested in a concat
    assert pc(lambda s: 5 % s, "x") == []  # non-constant %-template
    assert pc(lambda s: PCT_TRAILING % s, "x") == []  # dangling %
    assert pc(lambda n: "%d" % n, "007") == []  # noqa: UP031  # not canonical
    assert pc(lambda s: s - 1, "x") == []  # not a string operator
    assert pc(lambda t: t[0] * t[1], "xx") == []  # no constant side
    assert pc(lambda n: "xy" * n, "xyx") == []  # length not divisible
    assert pc(lambda s: s.center(5), "  x  ") == []  # unsupported method
    assert pc(lambda s: s + s[0], "aa") == []  # mixes whole-arg and indexing


def test_case_ops_with_no_verifying_folding():
    # no case-folding of "aBc" maps to it under .upper()
    assert pc(lambda s: s.upper(), "aBc") == []


def test_zfill_edge_cases():
    assert pc(lambda s: s.zfill(5), "ab") == []  # too short to be a zfill
    assert pc(lambda s: s.zfill(True), "x") == []  # width must be an int
    # stripping the leading zero would move it past a non-digit
    assert pc(lambda s: s.zfill(3), "0-1") == ["0-1"]


def test_removeprefix_candidates_in_order():
    assert pc(lambda s: s.removeprefix("p-"), "x") == ["x", "p-x"]
    assert pc(lambda s: s.removeprefix("p-"), "p-x") == ["p-p-x"]


def test_join_candidates():
    assert pc(lambda ls: ",".join(ls), "a,b") == [["a", "b"], ("a", "b")]
    assert pc(lambda ls: "".join(ls), "ab") == [["a", "b"], ("a", "b")]


def test_functions_of_other_arities_are_rejected():
    with pytest.raises(CannotInvert):
        pc(lambda *args: "x", "x")
    with pytest.raises(CannotInvert):
        pc(lambda s, **kw: "x", "x")
