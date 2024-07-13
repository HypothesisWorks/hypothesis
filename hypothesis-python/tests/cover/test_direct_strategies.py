# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import collections
import decimal
import enum
import fractions
import math
from datetime import date, datetime, time, timedelta
from ipaddress import IPv4Network, IPv6Network

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.vendor.pretty import pretty

from tests.common.debug import check_can_generate_examples, minimal

# Use `pretty` instead of `repr` for building test names, so that set and dict
# parameters print consistently across multiple worker processes with different
# PYTHONHASHSEED values.


def fn_test(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        ("fn", "args"),
        fnkwargs,
        ids=[
            "{}({})".format(fn.__name__, ", ".join(map(pretty, args)))
            for fn, args in fnkwargs
        ],
    )


def fn_ktest(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        ("fn", "kwargs"),
        fnkwargs,
        ids=[f"{fn.__name__}(**{pretty(kwargs)})" for fn, kwargs in fnkwargs],
    )


@fn_ktest(
    (st.integers, {"min_value": math.nan}),
    (st.integers, {"min_value": 2, "max_value": 1}),
    (st.integers, {"min_value": math.nan}),
    (st.integers, {"max_value": math.nan}),
    (st.integers, {"min_value": decimal.Decimal("1.5")}),
    (st.integers, {"max_value": decimal.Decimal("1.5")}),
    (st.integers, {"min_value": -1.5, "max_value": -0.5}),
    (st.integers, {"min_value": 0.1, "max_value": 0.2}),
    (st.dates, {"min_value": "fish"}),
    (st.dates, {"max_value": "fish"}),
    (st.dates, {"min_value": date(2017, 8, 22), "max_value": date(2017, 8, 21)}),
    (st.datetimes, {"min_value": "fish"}),
    (st.datetimes, {"max_value": "fish"}),
    (st.datetimes, {"allow_imaginary": 0}),
    (
        st.datetimes,
        {"min_value": datetime(2017, 8, 22), "max_value": datetime(2017, 8, 21)},
    ),
    (st.decimals, {"min_value": math.nan}),
    (st.decimals, {"max_value": math.nan}),
    (st.decimals, {"min_value": 2, "max_value": 1}),
    (st.decimals, {"max_value": "-snan"}),
    (st.decimals, {"max_value": complex(1, 2)}),
    (st.decimals, {"places": -1}),
    (st.decimals, {"places": 0.5}),
    (st.decimals, {"max_value": 0.0, "min_value": 1.0}),
    (st.decimals, {"min_value": 1.0, "max_value": 0.0}),
    (st.decimals, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (st.decimals, {"min_value": "inf"}),
    (st.decimals, {"max_value": "-inf"}),
    (st.decimals, {"min_value": "-inf", "allow_infinity": False}),
    (st.decimals, {"max_value": "inf", "allow_infinity": False}),
    (st.decimals, {"min_value": complex(1, 2)}),
    (st.decimals, {"min_value": "0.1", "max_value": "0.9", "places": 0}),
    (
        st.dictionaries,
        {"keys": st.booleans(), "values": st.booleans(), "min_size": 10, "max_size": 1},
    ),
    (st.floats, {"min_value": math.nan}),
    (st.floats, {"max_value": math.nan}),
    (st.floats, {"min_value": complex(1, 2)}),
    (st.floats, {"max_value": complex(1, 2)}),
    (st.floats, {"exclude_min": None}),
    (st.floats, {"exclude_max": None}),
    (st.floats, {"exclude_min": True}),  # because min_value=None
    (st.floats, {"exclude_max": True}),  # because max_value=None
    (st.floats, {"min_value": 1.8, "width": 32}),
    (st.floats, {"max_value": 1.8, "width": 32}),
    (st.fractions, {"min_value": 2, "max_value": 1}),
    (st.fractions, {"min_value": math.nan}),
    (st.fractions, {"max_value": math.nan}),
    (st.fractions, {"max_denominator": 0}),
    (st.fractions, {"max_denominator": 1.5}),
    (st.fractions, {"min_value": complex(1, 2)}),
    (st.fractions, {"min_value": "1/3", "max_value": "1/2", "max_denominator": 2}),
    (st.fractions, {"min_value": "0", "max_value": "1/3", "max_denominator": 2}),
    (st.fractions, {"min_value": "1/3", "max_value": "1/3", "max_denominator": 2}),
    (st.lists, {"elements": st.integers(), "min_size": 10, "max_size": 9}),
    (st.lists, {"elements": st.integers(), "min_size": -10, "max_size": -9}),
    (st.lists, {"elements": st.integers(), "max_size": -9}),
    (st.lists, {"elements": st.integers(), "min_size": -10}),
    (st.lists, {"elements": st.integers(), "min_size": math.nan}),
    (st.lists, {"elements": st.nothing(), "max_size": 1}),
    (st.lists, {"elements": "hi"}),
    (st.lists, {"elements": st.integers(), "unique_by": 1}),
    (st.lists, {"elements": st.integers(), "unique_by": ()}),
    (st.lists, {"elements": st.integers(), "unique_by": (1,)}),
    (st.lists, {"elements": st.sampled_from([0, 1]), "min_size": 3, "unique": True}),
    (st.lists, {"elements": st.none(), "min_size": 100_000}),
    (st.lists, {"elements": st.none(), "min_size": 100_000, "unique": True}),
    (
        st.lists,
        {"elements": st.sampled_from([1, 2]), "min_size": 100_000, "unique": True},
    ),
    (st.text, {"min_size": 10, "max_size": 9}),
    (st.text, {"alphabet": [1]}),
    (st.text, {"alphabet": ["abc"]}),
    (st.text, {"alphabet": st.just("abc")}),
    (st.text, {"alphabet": st.sampled_from(["abc", "def"])}),
    (st.text, {"alphabet": st.just(123)}),
    (st.text, {"alphabet": st.sampled_from([123, 456])}),
    (st.text, {"alphabet": st.builds(lambda: "abc")}),
    (st.text, {"alphabet": st.builds(lambda: 123)}),
    (st.text, {"alphabet": "abc", "min_size": 100_000}),
    (st.from_regex, {"regex": 123}),
    (st.from_regex, {"regex": b"abc", "alphabet": "abc"}),
    (st.from_regex, {"regex": b"abc", "alphabet": b"def"}),
    (st.from_regex, {"regex": "abc", "alphabet": "def"}),
    (st.from_regex, {"regex": "aa|bb", "alphabet": "c"}),
    (st.from_regex, {"regex": "[abc]", "alphabet": "def"}),
    (st.from_regex, {"regex": "[ab]x[de]", "alphabet": "abcdef"}),
    (st.from_regex, {"regex": "...", "alphabet": st.builds(lambda: "a")}),
    (st.from_regex, {"regex": "abc", "alphabet": st.sampled_from("def")}),
    (st.from_regex, {"regex": "abc", "alphabet": st.characters(min_codepoint=128)}),
    (st.from_regex, {"regex": "abc", "alphabet": 123}),
    (st.binary, {"min_size": 10, "max_size": 9}),
    (st.floats, {"min_value": math.nan}),
    (st.floats, {"min_value": "0"}),
    (st.floats, {"max_value": "0"}),
    (st.floats, {"min_value": 0.0, "max_value": -0.0}),
    (st.floats, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (st.floats, {"max_value": 0.0, "min_value": 1.0}),
    (st.floats, {"min_value": 0.0, "allow_nan": True}),
    (st.floats, {"max_value": 0.0, "allow_nan": True}),
    (st.floats, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (st.floats, {"min_value": math.inf, "allow_infinity": False}),
    (st.floats, {"max_value": -math.inf, "allow_infinity": False}),
    (st.complex_numbers, {"min_magnitude": None}),
    (st.complex_numbers, {"min_magnitude": math.nan}),
    (st.complex_numbers, {"max_magnitude": math.nan}),
    (st.complex_numbers, {"max_magnitude": complex(1, 2)}),
    (st.complex_numbers, {"min_magnitude": -1}),
    (st.complex_numbers, {"max_magnitude": -1}),
    (st.complex_numbers, {"min_magnitude": 3, "max_magnitude": 2}),
    (st.complex_numbers, {"max_magnitude": 2, "allow_infinity": True}),
    (st.complex_numbers, {"max_magnitude": 2, "allow_nan": True}),
    (st.complex_numbers, {"width": None}),
    # Conceivable mistake when misunderstanding width for individual component widths:
    (st.complex_numbers, {"width": 16}),
    # Unsupported as of now:
    (st.complex_numbers, {"width": 196}),
    (st.complex_numbers, {"width": 256}),
    (st.fixed_dictionaries, {"mapping": "fish"}),
    (st.fixed_dictionaries, {"mapping": {1: "fish"}}),
    (st.fixed_dictionaries, {"mapping": {}, "optional": "fish"}),
    (st.fixed_dictionaries, {"mapping": {}, "optional": {1: "fish"}}),
    (st.fixed_dictionaries, {"mapping": {}, "optional": collections.OrderedDict()}),
    (st.fixed_dictionaries, {"mapping": {1: st.none()}, "optional": {1: st.none()}}),
    (st.dictionaries, {"keys": st.integers(), "values": 1}),
    (st.dictionaries, {"keys": 1, "values": st.integers()}),
    (st.text, {"alphabet": "", "min_size": 1}),
    (st.timedeltas, {"min_value": "fish"}),
    (st.timedeltas, {"max_value": "fish"}),
    (
        st.timedeltas,
        {"min_value": timedelta(hours=1), "max_value": timedelta(minutes=1)},
    ),
    (st.times, {"min_value": "fish"}),
    (st.times, {"max_value": "fish"}),
    (st.times, {"min_value": time(2, 0), "max_value": time(1, 0)}),
    (st.uuids, {"version": 6}),
    (st.characters, {"min_codepoint": -1}),
    (st.characters, {"min_codepoint": "1"}),
    (st.characters, {"max_codepoint": -1}),
    (st.characters, {"max_codepoint": "1"}),
    (st.characters, {"categories": []}),
    (st.characters, {"categories": ["Nd"], "exclude_categories": ["Nd"]}),
    (st.characters, {"whitelist_categories": ["Nd"], "blacklist_categories": ["Nd"]}),
    (st.characters, {"include_characters": "a", "blacklist_characters": "b"}),
    (st.characters, {"codec": 100}),
    (st.characters, {"codec": "this is not a valid codec name"}),
    (st.characters, {"codec": "ascii", "include_characters": "é"}),
    (st.characters, {"codec": "utf-8", "categories": "Cs"}),
    (st.slices, {"size": None}),
    (st.slices, {"size": "chips"}),
    (st.slices, {"size": -1}),
    (st.slices, {"size": 2.3}),
    (st.sampled_from, {"elements": ()}),
    (st.ip_addresses, {"v": "4"}),
    (st.ip_addresses, {"v": 4.0}),
    (st.ip_addresses, {"v": 5}),
    (st.ip_addresses, {"v": 4, "network": "::/64"}),
    (st.ip_addresses, {"v": 6, "network": "127.0.0.0/8"}),
    (st.ip_addresses, {"network": b"127.0.0.0/8"}),  # only unicode strings are valid
    (st.ip_addresses, {"network": b"::/64"}),
    (st.randoms, {"use_true_random": "False"}),
    (st.randoms, {"note_method_calls": "True"}),
)
def test_validates_keyword_arguments(fn, kwargs):
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(fn(**kwargs))


@fn_ktest(
    (st.integers, {"min_value": 0}),
    (st.integers, {"min_value": 11}),
    (st.integers, {"min_value": 11, "max_value": 100}),
    (st.integers, {"max_value": 0}),
    (st.integers, {"min_value": -2, "max_value": -1}),
    (st.decimals, {"min_value": 1.0, "max_value": 1.5}),
    (st.decimals, {"min_value": "1.0", "max_value": "1.5"}),
    (st.decimals, {"min_value": decimal.Decimal("1.5")}),
    (st.decimals, {"max_value": 1.0, "min_value": -1.0, "allow_infinity": False}),
    (st.decimals, {"min_value": 1.0, "allow_nan": False}),
    (st.decimals, {"max_value": 1.0, "allow_nan": False}),
    (st.decimals, {"max_value": 1.0, "min_value": -1.0, "allow_nan": False}),
    (st.decimals, {"min_value": "-inf"}),
    (st.decimals, {"max_value": "inf"}),
    (st.fractions, {"min_value": -1, "max_value": 1, "max_denominator": 1000}),
    (st.fractions, {"min_value": 1, "max_value": 1}),
    (st.fractions, {"min_value": 1, "max_value": 1, "max_denominator": 2}),
    (st.fractions, {"min_value": 1.0}),
    (st.fractions, {"min_value": decimal.Decimal("1.0")}),
    (st.fractions, {"min_value": fractions.Fraction(1, 2)}),
    (st.fractions, {"min_value": "1/2", "max_denominator": 2}),
    (st.fractions, {"max_value": "1/2", "max_denominator": 3}),
    (st.lists, {"elements": st.nothing(), "max_size": 0}),
    (st.lists, {"elements": st.integers()}),
    (st.lists, {"elements": st.integers(), "max_size": 5}),
    (st.lists, {"elements": st.booleans(), "min_size": 5}),
    (st.lists, {"elements": st.booleans(), "min_size": 5, "max_size": 10}),
    (st.sets, {"min_size": 10, "max_size": 10, "elements": st.integers()}),
    (st.booleans, {}),
    (st.just, {"value": "hi"}),
    (st.integers, {"min_value": 12, "max_value": 12}),
    (st.floats, {}),
    (st.floats, {"min_value": 1.0}),
    (st.floats, {"max_value": 1.0}),
    (st.floats, {"min_value": math.inf}),
    (st.floats, {"max_value": -math.inf}),
    (st.floats, {"max_value": 1.0, "min_value": -1.0}),
    (st.floats, {"max_value": 1.0, "min_value": -1.0, "allow_infinity": False}),
    (st.floats, {"min_value": 1.0, "allow_nan": False}),
    (st.floats, {"max_value": 1.0, "allow_nan": False}),
    (st.floats, {"max_value": 1.0, "min_value": -1.0, "allow_nan": False}),
    (st.complex_numbers, {}),
    (st.complex_numbers, {"min_magnitude": 3, "max_magnitude": 3}),
    (st.complex_numbers, {"max_magnitude": 0}),
    (st.complex_numbers, {"allow_nan": True}),
    (st.complex_numbers, {"allow_nan": True, "allow_infinity": True}),
    (st.complex_numbers, {"allow_nan": True, "allow_infinity": False}),
    (st.complex_numbers, {"allow_nan": False}),
    (st.complex_numbers, {"allow_nan": False, "allow_infinity": True}),
    (st.complex_numbers, {"allow_nan": False, "allow_infinity": False}),
    (st.complex_numbers, {"max_magnitude": math.inf, "allow_infinity": True}),
    (st.complex_numbers, {"width": 32}),
    (st.complex_numbers, {"width": 64}),
    (st.complex_numbers, {"width": 128}),
    (st.sampled_from, {"elements": [1]}),
    (st.sampled_from, {"elements": [1, 2, 3]}),
    (st.fixed_dictionaries, {"mapping": {1: st.integers()}}),
    (st.dictionaries, {"keys": st.booleans(), "values": st.integers()}),
    (st.text, {"alphabet": "abc"}),
    (st.text, {"alphabet": set("abc")}),
    (st.text, {"alphabet": ""}),
    (st.text, {"alphabet": st.just("a")}),
    (st.text, {"alphabet": st.sampled_from("abc")}),
    (st.text, {"alphabet": st.builds(lambda: "a")}),
    (st.characters, {"codec": "ascii"}),
    (st.characters, {"codec": "latin1"}),
    (st.characters, {"categories": ["N"]}),
    (st.characters, {"exclude_categories": []}),
    (st.characters, {"whitelist_characters": "a", "codec": "ascii"}),
    (st.characters, {"blacklist_characters": "a"}),
    (st.characters, {"whitelist_categories": ["Nd"]}),
    (st.characters, {"blacklist_categories": ["Nd"]}),
    (st.from_regex, {"regex": "abc", "alphabet": "abc"}),
    (st.from_regex, {"regex": "abc", "alphabet": "abcdef"}),
    (st.from_regex, {"regex": "[abc]", "alphabet": "abcdef"}),
    (st.from_regex, {"regex": "[a-f]", "alphabet": "abef"}),
    (st.from_regex, {"regex": "[a-d]", "alphabet": "def"}),
    (st.from_regex, {"regex": "[f-z]", "alphabet": "def"}),
    (st.from_regex, {"regex": "abc", "alphabet": st.sampled_from("abc")}),
    (st.from_regex, {"regex": "abc", "alphabet": st.characters(codec="ascii")}),
    (st.ip_addresses, {}),
    (st.ip_addresses, {"v": 4}),
    (st.ip_addresses, {"v": 6}),
    (st.ip_addresses, {"network": "127.0.0.0/8"}),
    (st.ip_addresses, {"network": "::/64"}),
    (st.ip_addresses, {"v": 4, "network": "127.0.0.0/8"}),
    (st.ip_addresses, {"v": 6, "network": "::/64"}),
    (st.ip_addresses, {"network": IPv4Network("127.0.0.0/8")}),
    (st.ip_addresses, {"network": IPv6Network("::/64")}),
    (st.ip_addresses, {"v": 4, "network": IPv4Network("127.0.0.0/8")}),
    (st.ip_addresses, {"v": 6, "network": IPv6Network("::/64")}),
)
def test_produces_valid_examples_from_keyword(fn, kwargs):
    check_can_generate_examples(fn(**kwargs))


@fn_test(
    (st.one_of, (1,)),
    (st.one_of, (1, st.integers())),
    (st.tuples, (1,)),
)
def test_validates_args(fn, args):
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(fn(*args))


@fn_test(
    (st.one_of, (st.booleans(), st.tuples(st.booleans()))),
    (st.one_of, (st.booleans(),)),
    (st.text, ()),
    (st.binary, ()),
    (st.builds, (lambda x, y: x + y, st.integers(), st.integers())),
)
def test_produces_valid_examples_from_args(fn, args):
    check_can_generate_examples(fn(*args))


def test_build_class_with_target_kwarg():
    NamedTupleWithTargetField = collections.namedtuple("Something", ["target"])
    check_can_generate_examples(
        st.builds(NamedTupleWithTargetField, target=st.integers())
    )


def test_builds_raises_with_no_target():
    with pytest.raises(TypeError):
        check_can_generate_examples(st.builds())


@pytest.mark.parametrize("non_callable", [1, "abc", st.integers()])
def test_builds_raises_if_non_callable_as_target_kwarg(non_callable):
    with pytest.raises(TypeError):
        check_can_generate_examples(st.builds(target=non_callable))


@pytest.mark.parametrize("non_callable", [1, "abc", st.integers()])
def test_builds_raises_if_non_callable_as_first_arg(non_callable):
    # If there are any positional arguments, then the target (which must be
    # callable) must be specified as the first one.
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.builds(non_callable, target=lambda x: x))


def test_tuples_raise_error_on_bad_kwargs():
    with pytest.raises(TypeError):
        st.tuples(stuff="things")


@given(st.lists(st.booleans(), min_size=10, max_size=10))
def test_has_specified_length(xs):
    assert len(xs) == 10


@given(st.integers(max_value=100))
@settings(max_examples=100)
def test_has_upper_bound(x):
    assert x <= 100


@given(st.integers(min_value=100))
def test_has_lower_bound(x):
    assert x >= 100


@given(st.integers(min_value=1, max_value=2))
def test_is_in_bounds(x):
    assert 1 <= x <= 2


@given(st.fractions(min_value=-1, max_value=1, max_denominator=1000))
def test_fraction_is_in_bounds(x):
    assert -1 <= x <= 1
    assert abs(x.denominator) <= 1000


@given(st.fractions(min_value=fractions.Fraction(1, 2)))
def test_fraction_gt_positive(x):
    assert fractions.Fraction(1, 2) <= x


@given(st.fractions(max_value=fractions.Fraction(-1, 2)))
def test_fraction_lt_negative(x):
    assert x <= fractions.Fraction(-1, 2)


@given(st.decimals(min_value=-1.5, max_value=1.5))
def test_decimal_is_in_bounds(x):
    assert decimal.Decimal("-1.5") <= x <= decimal.Decimal("1.5")


def test_float_can_find_max_value_inf():
    assert minimal(st.floats(max_value=math.inf), math.isinf) == float("inf")
    assert minimal(st.floats(min_value=0.0), math.isinf) == math.inf


def test_float_can_find_min_value_inf():
    minimal(st.floats(), lambda x: x < 0 and math.isinf(x))
    minimal(st.floats(min_value=-math.inf, max_value=0.0), math.isinf)


def test_can_find_none_list():
    assert minimal(st.lists(st.none()), lambda x: len(x) >= 3) == [None] * 3


def test_fractions():
    assert minimal(st.fractions(), lambda f: f >= 1) == 1


def test_decimals():
    assert minimal(st.decimals(), lambda f: f.is_finite() and f >= 1) == 1


def test_non_float_decimal():
    minimal(st.decimals(), lambda d: d.is_finite() and decimal.Decimal(float(d)) != d)


def test_produces_dictionaries_of_at_least_minimum_size():
    t = minimal(
        st.dictionaries(st.booleans(), st.integers(), min_size=2),
    )
    assert t == {False: 0, True: 0}


@given(st.dictionaries(st.integers(), st.integers(), max_size=5))
@settings(max_examples=50)
def test_dictionaries_respect_size(d):
    assert len(d) <= 5


@given(st.dictionaries(st.integers(), st.integers(), max_size=0))
@settings(max_examples=50)
def test_dictionaries_respect_zero_size(d):
    assert len(d) <= 5


@given(st.lists(st.none(), max_size=5))
def test_none_lists_respect_max_size(ls):
    assert len(ls) <= 5


@given(st.lists(st.none(), max_size=5, min_size=1))
def test_none_lists_respect_max_and_min_size(ls):
    assert 1 <= len(ls) <= 5


@given(st.iterables(st.integers(), max_size=5, min_size=1))
def test_iterables_are_exhaustible(it):
    for _ in it:
        pass
    with pytest.raises(StopIteration):
        next(it)


def test_minimal_iterable():
    assert list(minimal(st.iterables(st.integers()))) == []


@pytest.mark.parametrize("parameter_name", ["min_value", "max_value"])
@pytest.mark.parametrize("value", [-1, 0, 1])
def test_no_infinity_for_min_max_values(value, parameter_name):
    kwargs = {"allow_infinity": False, parameter_name: value}

    @given(st.floats(**kwargs))
    def test_not_infinite(xs):
        assert not math.isinf(xs)

    test_not_infinite()


@pytest.mark.parametrize("parameter_name", ["min_value", "max_value"])
@pytest.mark.parametrize("value", [-1, 0, 1])
def test_no_nan_for_min_max_values(value, parameter_name):
    kwargs = {"allow_nan": False, parameter_name: value}

    @given(st.floats(**kwargs))
    def test_not_nan(xs):
        assert not math.isnan(xs)

    test_not_nan()


class Sneaky:
    """It's like a strategy, but it's not a strategy."""

    is_empty = False
    depth = 0
    label = 0

    def do_draw(self, data):
        pass

    def validate(self):
        pass


@pytest.mark.parametrize("value", [5, Sneaky()])
@pytest.mark.parametrize("label", [None, "not a strategy"])
@given(data=st.data())
def test_data_explicitly_rejects_non_strategies(data, value, label):
    with pytest.raises(InvalidArgument):
        data.draw(value, label=label)


@given(st.integers().filter(bool).filter(lambda x: x % 3))
def test_chained_filter(x):
    assert x
    assert x % 3


def test_chained_filter_tracks_all_conditions():
    s = st.integers().filter(bool).filter(lambda x: x % 3)
    assert len(s.wrapped_strategy.flat_conditions) == 2


@pytest.mark.parametrize("version", [4, 6])
@given(data=st.data())
def test_ipaddress_from_network_is_always_correct_version(data, version):
    ip = data.draw(st.ip_addresses(v=version), label="address")
    assert ip.version == version


@given(data=st.data(), network=st.from_type(IPv4Network) | st.from_type(IPv6Network))
def test_ipaddress_from_network_is_always_in_network(data, network):
    ip = data.draw(st.ip_addresses(network=network), label="address")
    assert ip in network
    assert ip.version == network.version


class AnEnum(enum.Enum):
    a = 1


def requires_arg(value):
    """Similar to the enum.Enum.__call__ method."""


@given(st.data())
def test_builds_error_messages(data):
    # If we call them directly, we get a simple TypeError in both cases
    with pytest.raises(TypeError):
        requires_arg()
    with pytest.raises(TypeError):
        AnEnum()
    # But we have an improved error message if you try to build an Enum
    assert issubclass(InvalidArgument, TypeError)  # it's a valid substitution
    with pytest.raises(TypeError):  # which only applies to enums
        data.draw(st.builds(requires_arg))
    with pytest.raises(
        InvalidArgument,
        match=r".* try using sampled_from\(.+\) instead of builds\(.+\)",
    ):
        data.draw(st.builds(AnEnum))
    # and sampled_from() does in fact work
    data.draw(st.sampled_from(AnEnum))
