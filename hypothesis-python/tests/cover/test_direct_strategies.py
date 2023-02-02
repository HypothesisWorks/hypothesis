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

from hypothesis import given, settings, strategies as ds
from hypothesis.errors import InvalidArgument
from hypothesis.vendor.pretty import pretty

from tests.common.debug import minimal

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
    (ds.integers, {"min_value": math.nan}),
    (ds.integers, {"min_value": 2, "max_value": 1}),
    (ds.integers, {"min_value": math.nan}),
    (ds.integers, {"max_value": math.nan}),
    (ds.integers, {"min_value": decimal.Decimal("1.5")}),
    (ds.integers, {"max_value": decimal.Decimal("1.5")}),
    (ds.integers, {"min_value": -1.5, "max_value": -0.5}),
    (ds.integers, {"min_value": 0.1, "max_value": 0.2}),
    (ds.dates, {"min_value": "fish"}),
    (ds.dates, {"max_value": "fish"}),
    (ds.dates, {"min_value": date(2017, 8, 22), "max_value": date(2017, 8, 21)}),
    (ds.datetimes, {"min_value": "fish"}),
    (ds.datetimes, {"max_value": "fish"}),
    (ds.datetimes, {"allow_imaginary": 0}),
    (
        ds.datetimes,
        {"min_value": datetime(2017, 8, 22), "max_value": datetime(2017, 8, 21)},
    ),
    (ds.decimals, {"min_value": math.nan}),
    (ds.decimals, {"max_value": math.nan}),
    (ds.decimals, {"min_value": 2, "max_value": 1}),
    (ds.decimals, {"max_value": "-snan"}),
    (ds.decimals, {"max_value": complex(1, 2)}),
    (ds.decimals, {"places": -1}),
    (ds.decimals, {"places": 0.5}),
    (ds.decimals, {"max_value": 0.0, "min_value": 1.0}),
    (ds.decimals, {"min_value": 1.0, "max_value": 0.0}),
    (ds.decimals, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (ds.decimals, {"min_value": "inf"}),
    (ds.decimals, {"max_value": "-inf"}),
    (ds.decimals, {"min_value": "-inf", "allow_infinity": False}),
    (ds.decimals, {"max_value": "inf", "allow_infinity": False}),
    (ds.decimals, {"min_value": complex(1, 2)}),
    (ds.decimals, {"min_value": "0.1", "max_value": "0.9", "places": 0}),
    (
        ds.dictionaries,
        {"keys": ds.booleans(), "values": ds.booleans(), "min_size": 10, "max_size": 1},
    ),
    (ds.floats, {"min_value": math.nan}),
    (ds.floats, {"max_value": math.nan}),
    (ds.floats, {"min_value": complex(1, 2)}),
    (ds.floats, {"max_value": complex(1, 2)}),
    (ds.floats, {"exclude_min": None}),
    (ds.floats, {"exclude_max": None}),
    (ds.floats, {"exclude_min": True}),  # because min_value=None
    (ds.floats, {"exclude_max": True}),  # because max_value=None
    (ds.floats, {"min_value": 1.8, "width": 32}),
    (ds.floats, {"max_value": 1.8, "width": 32}),
    (ds.complex_numbers, {"min_magnitude": 1.8, "width": 64}),
    (ds.complex_numbers, {"max_magnitude": 1.8, "width": 64}),
    (ds.fractions, {"min_value": 2, "max_value": 1}),
    (ds.fractions, {"min_value": math.nan}),
    (ds.fractions, {"max_value": math.nan}),
    (ds.fractions, {"max_denominator": 0}),
    (ds.fractions, {"max_denominator": 1.5}),
    (ds.fractions, {"min_value": complex(1, 2)}),
    (ds.fractions, {"min_value": "1/3", "max_value": "1/2", "max_denominator": 2}),
    (ds.fractions, {"min_value": "0", "max_value": "1/3", "max_denominator": 2}),
    (ds.fractions, {"min_value": "1/3", "max_value": "1/3", "max_denominator": 2}),
    (ds.lists, {"elements": ds.integers(), "min_size": 10, "max_size": 9}),
    (ds.lists, {"elements": ds.integers(), "min_size": -10, "max_size": -9}),
    (ds.lists, {"elements": ds.integers(), "max_size": -9}),
    (ds.lists, {"elements": ds.integers(), "min_size": -10}),
    (ds.lists, {"elements": ds.integers(), "min_size": math.nan}),
    (ds.lists, {"elements": ds.nothing(), "max_size": 1}),
    (ds.lists, {"elements": "hi"}),
    (ds.lists, {"elements": ds.integers(), "unique_by": 1}),
    (ds.lists, {"elements": ds.integers(), "unique_by": ()}),
    (ds.lists, {"elements": ds.integers(), "unique_by": (1,)}),
    (ds.lists, {"elements": ds.sampled_from([0, 1]), "min_size": 3, "unique": True}),
    (ds.text, {"min_size": 10, "max_size": 9}),
    (ds.text, {"alphabet": [1]}),
    (ds.text, {"alphabet": ["abc"]}),
    (ds.text, {"alphabet": ds.just("abc")}),
    (ds.text, {"alphabet": ds.sampled_from(["abc", "def"])}),
    (ds.text, {"alphabet": ds.just(123)}),
    (ds.text, {"alphabet": ds.sampled_from([123, 456])}),
    (ds.text, {"alphabet": ds.builds(lambda: "abc")}),
    (ds.text, {"alphabet": ds.builds(lambda: 123)}),
    (ds.binary, {"min_size": 10, "max_size": 9}),
    (ds.floats, {"min_value": math.nan}),
    (ds.floats, {"min_value": "0"}),
    (ds.floats, {"max_value": "0"}),
    (ds.floats, {"min_value": 0.0, "max_value": -0.0}),
    (ds.floats, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (ds.floats, {"max_value": 0.0, "min_value": 1.0}),
    (ds.floats, {"min_value": 0.0, "allow_nan": True}),
    (ds.floats, {"max_value": 0.0, "allow_nan": True}),
    (ds.floats, {"min_value": 0.0, "max_value": 1.0, "allow_infinity": True}),
    (ds.floats, {"min_value": math.inf, "allow_infinity": False}),
    (ds.floats, {"max_value": -math.inf, "allow_infinity": False}),
    (ds.complex_numbers, {"min_magnitude": None}),
    (ds.complex_numbers, {"min_magnitude": math.nan}),
    (ds.complex_numbers, {"max_magnitude": math.nan}),
    (ds.complex_numbers, {"max_magnitude": complex(1, 2)}),
    (ds.complex_numbers, {"min_magnitude": -1}),
    (ds.complex_numbers, {"max_magnitude": -1}),
    (ds.complex_numbers, {"min_magnitude": 3, "max_magnitude": 2}),
    (ds.complex_numbers, {"max_magnitude": 2, "allow_infinity": True}),
    (ds.complex_numbers, {"max_magnitude": 2, "allow_nan": True}),
    (ds.complex_numbers, {"width": None}),
    # Conceivable mistake when misunderstanding width for individual component widths:
    (ds.complex_numbers, {"width": 16}),
    # Unsupported as of now:
    (ds.complex_numbers, {"width": 196}),
    (ds.complex_numbers, {"width": 256}),
    (ds.fixed_dictionaries, {"mapping": "fish"}),
    (ds.fixed_dictionaries, {"mapping": {1: "fish"}}),
    (ds.fixed_dictionaries, {"mapping": {}, "optional": "fish"}),
    (ds.fixed_dictionaries, {"mapping": {}, "optional": {1: "fish"}}),
    (ds.fixed_dictionaries, {"mapping": {}, "optional": collections.OrderedDict()}),
    (ds.fixed_dictionaries, {"mapping": {1: ds.none()}, "optional": {1: ds.none()}}),
    (ds.dictionaries, {"keys": ds.integers(), "values": 1}),
    (ds.dictionaries, {"keys": 1, "values": ds.integers()}),
    (ds.text, {"alphabet": "", "min_size": 1}),
    (ds.timedeltas, {"min_value": "fish"}),
    (ds.timedeltas, {"max_value": "fish"}),
    (
        ds.timedeltas,
        {"min_value": timedelta(hours=1), "max_value": timedelta(minutes=1)},
    ),
    (ds.times, {"min_value": "fish"}),
    (ds.times, {"max_value": "fish"}),
    (ds.times, {"min_value": time(2, 0), "max_value": time(1, 0)}),
    (ds.uuids, {"version": 6}),
    (ds.characters, {"min_codepoint": -1}),
    (ds.characters, {"min_codepoint": "1"}),
    (ds.characters, {"max_codepoint": -1}),
    (ds.characters, {"max_codepoint": "1"}),
    (ds.characters, {"whitelist_categories": []}),
    (ds.characters, {"whitelist_categories": ["Nd"], "blacklist_categories": ["Nd"]}),
    (ds.slices, {"size": None}),
    (ds.slices, {"size": "chips"}),
    (ds.slices, {"size": -1}),
    (ds.slices, {"size": 2.3}),
    (ds.sampled_from, {"elements": ()}),
    (ds.ip_addresses, {"v": "4"}),
    (ds.ip_addresses, {"v": 4.0}),
    (ds.ip_addresses, {"v": 5}),
    (ds.ip_addresses, {"v": 4, "network": "::/64"}),
    (ds.ip_addresses, {"v": 6, "network": "127.0.0.0/8"}),
    (ds.ip_addresses, {"network": b"127.0.0.0/8"}),  # only unicode strings are valid
    (ds.ip_addresses, {"network": b"::/64"}),
    (ds.randoms, {"use_true_random": "False"}),
    (ds.randoms, {"note_method_calls": "True"}),
)
def test_validates_keyword_arguments(fn, kwargs):
    with pytest.raises(InvalidArgument):
        fn(**kwargs).example()


@fn_ktest(
    (ds.integers, {"min_value": 0}),
    (ds.integers, {"min_value": 11}),
    (ds.integers, {"min_value": 11, "max_value": 100}),
    (ds.integers, {"max_value": 0}),
    (ds.integers, {"min_value": -2, "max_value": -1}),
    (ds.decimals, {"min_value": 1.0, "max_value": 1.5}),
    (ds.decimals, {"min_value": "1.0", "max_value": "1.5"}),
    (ds.decimals, {"min_value": decimal.Decimal("1.5")}),
    (ds.decimals, {"max_value": 1.0, "min_value": -1.0, "allow_infinity": False}),
    (ds.decimals, {"min_value": 1.0, "allow_nan": False}),
    (ds.decimals, {"max_value": 1.0, "allow_nan": False}),
    (ds.decimals, {"max_value": 1.0, "min_value": -1.0, "allow_nan": False}),
    (ds.decimals, {"min_value": "-inf"}),
    (ds.decimals, {"max_value": "inf"}),
    (ds.fractions, {"min_value": -1, "max_value": 1, "max_denominator": 1000}),
    (ds.fractions, {"min_value": 1, "max_value": 1}),
    (ds.fractions, {"min_value": 1, "max_value": 1, "max_denominator": 2}),
    (ds.fractions, {"min_value": 1.0}),
    (ds.fractions, {"min_value": decimal.Decimal("1.0")}),
    (ds.fractions, {"min_value": fractions.Fraction(1, 2)}),
    (ds.fractions, {"min_value": "1/2", "max_denominator": 2}),
    (ds.fractions, {"max_value": "1/2", "max_denominator": 3}),
    (ds.lists, {"elements": ds.nothing(), "max_size": 0}),
    (ds.lists, {"elements": ds.integers()}),
    (ds.lists, {"elements": ds.integers(), "max_size": 5}),
    (ds.lists, {"elements": ds.booleans(), "min_size": 5}),
    (ds.lists, {"elements": ds.booleans(), "min_size": 5, "max_size": 10}),
    (ds.sets, {"min_size": 10, "max_size": 10, "elements": ds.integers()}),
    (ds.booleans, {}),
    (ds.just, {"value": "hi"}),
    (ds.integers, {"min_value": 12, "max_value": 12}),
    (ds.floats, {}),
    (ds.floats, {"min_value": 1.0}),
    (ds.floats, {"max_value": 1.0}),
    (ds.floats, {"min_value": math.inf}),
    (ds.floats, {"max_value": -math.inf}),
    (ds.floats, {"max_value": 1.0, "min_value": -1.0}),
    (ds.floats, {"max_value": 1.0, "min_value": -1.0, "allow_infinity": False}),
    (ds.floats, {"min_value": 1.0, "allow_nan": False}),
    (ds.floats, {"max_value": 1.0, "allow_nan": False}),
    (ds.floats, {"max_value": 1.0, "min_value": -1.0, "allow_nan": False}),
    (ds.complex_numbers, {}),
    (ds.complex_numbers, {"min_magnitude": 3, "max_magnitude": 3}),
    (ds.complex_numbers, {"max_magnitude": 0}),
    (ds.complex_numbers, {"allow_nan": True}),
    (ds.complex_numbers, {"allow_nan": True, "allow_infinity": True}),
    (ds.complex_numbers, {"allow_nan": True, "allow_infinity": False}),
    (ds.complex_numbers, {"allow_nan": False}),
    (ds.complex_numbers, {"allow_nan": False, "allow_infinity": True}),
    (ds.complex_numbers, {"allow_nan": False, "allow_infinity": False}),
    (ds.complex_numbers, {"max_magnitude": math.inf, "allow_infinity": True}),
    (ds.complex_numbers, {"width": 32}),
    (ds.complex_numbers, {"width": 64}),
    (ds.complex_numbers, {"width": 128}),
    (ds.sampled_from, {"elements": [1]}),
    (ds.sampled_from, {"elements": [1, 2, 3]}),
    (ds.fixed_dictionaries, {"mapping": {1: ds.integers()}}),
    (ds.dictionaries, {"keys": ds.booleans(), "values": ds.integers()}),
    (ds.text, {"alphabet": "abc"}),
    (ds.text, {"alphabet": set("abc")}),
    (ds.text, {"alphabet": ""}),
    (ds.text, {"alphabet": ds.just("a")}),
    (ds.text, {"alphabet": ds.sampled_from("abc")}),
    (ds.text, {"alphabet": ds.builds(lambda: "a")}),
    (ds.characters, {"whitelist_categories": ["N"]}),
    (ds.characters, {"blacklist_categories": []}),
    (ds.ip_addresses, {}),
    (ds.ip_addresses, {"v": 4}),
    (ds.ip_addresses, {"v": 6}),
    (ds.ip_addresses, {"network": "127.0.0.0/8"}),
    (ds.ip_addresses, {"network": "::/64"}),
    (ds.ip_addresses, {"v": 4, "network": "127.0.0.0/8"}),
    (ds.ip_addresses, {"v": 6, "network": "::/64"}),
    (ds.ip_addresses, {"network": IPv4Network("127.0.0.0/8")}),
    (ds.ip_addresses, {"network": IPv6Network("::/64")}),
    (ds.ip_addresses, {"v": 4, "network": IPv4Network("127.0.0.0/8")}),
    (ds.ip_addresses, {"v": 6, "network": IPv6Network("::/64")}),
)
def test_produces_valid_examples_from_keyword(fn, kwargs):
    fn(**kwargs).example()


@fn_test(
    (ds.one_of, (1,)),
    (ds.one_of, (1, ds.integers())),
    (ds.tuples, (1,)),
)
def test_validates_args(fn, args):
    with pytest.raises(InvalidArgument):
        fn(*args).example()


@fn_test(
    (ds.one_of, (ds.booleans(), ds.tuples(ds.booleans()))),
    (ds.one_of, (ds.booleans(),)),
    (ds.text, ()),
    (ds.binary, ()),
    (ds.builds, (lambda x, y: x + y, ds.integers(), ds.integers())),
)
def test_produces_valid_examples_from_args(fn, args):
    fn(*args).example()


def test_build_class_with_target_kwarg():
    NamedTupleWithTargetField = collections.namedtuple("Something", ["target"])
    ds.builds(NamedTupleWithTargetField, target=ds.integers()).example()


def test_builds_raises_with_no_target():
    with pytest.raises(TypeError):
        ds.builds().example()


@pytest.mark.parametrize("non_callable", [1, "abc", ds.integers()])
def test_builds_raises_if_non_callable_as_target_kwarg(non_callable):
    with pytest.raises(TypeError):
        ds.builds(target=non_callable).example()


@pytest.mark.parametrize("non_callable", [1, "abc", ds.integers()])
def test_builds_raises_if_non_callable_as_first_arg(non_callable):
    # If there are any positional arguments, then the target (which must be
    # callable) must be specified as the first one.
    with pytest.raises(InvalidArgument):
        ds.builds(non_callable, target=lambda x: x).example()


def test_tuples_raise_error_on_bad_kwargs():
    with pytest.raises(TypeError):
        ds.tuples(stuff="things")


@given(ds.lists(ds.booleans(), min_size=10, max_size=10))
def test_has_specified_length(xs):
    assert len(xs) == 10


@given(ds.integers(max_value=100))
@settings(max_examples=100)
def test_has_upper_bound(x):
    assert x <= 100


@given(ds.integers(min_value=100))
def test_has_lower_bound(x):
    assert x >= 100


@given(ds.integers(min_value=1, max_value=2))
def test_is_in_bounds(x):
    assert 1 <= x <= 2


@given(ds.fractions(min_value=-1, max_value=1, max_denominator=1000))
def test_fraction_is_in_bounds(x):
    assert -1 <= x <= 1 and abs(x.denominator) <= 1000


@given(ds.fractions(min_value=fractions.Fraction(1, 2)))
def test_fraction_gt_positive(x):
    assert fractions.Fraction(1, 2) <= x


@given(ds.fractions(max_value=fractions.Fraction(-1, 2)))
def test_fraction_lt_negative(x):
    assert x <= fractions.Fraction(-1, 2)


@given(ds.decimals(min_value=-1.5, max_value=1.5))
def test_decimal_is_in_bounds(x):
    assert decimal.Decimal("-1.5") <= x <= decimal.Decimal("1.5")


def test_float_can_find_max_value_inf():
    assert minimal(ds.floats(max_value=math.inf), math.isinf) == float("inf")
    assert minimal(ds.floats(min_value=0.0), math.isinf) == math.inf


def test_float_can_find_min_value_inf():
    minimal(ds.floats(), lambda x: x < 0 and math.isinf(x))
    minimal(ds.floats(min_value=-math.inf, max_value=0.0), math.isinf)


def test_can_find_none_list():
    assert minimal(ds.lists(ds.none()), lambda x: len(x) >= 3) == [None] * 3


def test_fractions():
    assert minimal(ds.fractions(), lambda f: f >= 1) == 1


def test_decimals():
    assert minimal(ds.decimals(), lambda f: f.is_finite() and f >= 1) == 1


def test_non_float_decimal():
    minimal(ds.decimals(), lambda d: d.is_finite() and decimal.Decimal(float(d)) != d)


def test_produces_dictionaries_of_at_least_minimum_size():
    t = minimal(
        ds.dictionaries(ds.booleans(), ds.integers(), min_size=2), lambda x: True
    )
    assert t == {False: 0, True: 0}


@given(ds.dictionaries(ds.integers(), ds.integers(), max_size=5))
@settings(max_examples=50)
def test_dictionaries_respect_size(d):
    assert len(d) <= 5


@given(ds.dictionaries(ds.integers(), ds.integers(), max_size=0))
@settings(max_examples=50)
def test_dictionaries_respect_zero_size(d):
    assert len(d) <= 5


@given(ds.lists(ds.none(), max_size=5))
def test_none_lists_respect_max_size(ls):
    assert len(ls) <= 5


@given(ds.lists(ds.none(), max_size=5, min_size=1))
def test_none_lists_respect_max_and_min_size(ls):
    assert 1 <= len(ls) <= 5


@given(ds.iterables(ds.integers(), max_size=5, min_size=1))
def test_iterables_are_exhaustible(it):
    for _ in it:
        pass
    with pytest.raises(StopIteration):
        next(it)


def test_minimal_iterable():
    assert list(minimal(ds.iterables(ds.integers()), lambda x: True)) == []


@pytest.mark.parametrize("parameter_name", ["min_value", "max_value"])
@pytest.mark.parametrize("value", [-1, 0, 1])
def test_no_infinity_for_min_max_values(value, parameter_name):
    kwargs = {"allow_infinity": False, parameter_name: value}

    @given(ds.floats(**kwargs))
    def test_not_infinite(xs):
        assert not math.isinf(xs)

    test_not_infinite()


@pytest.mark.parametrize("parameter_name", ["min_value", "max_value"])
@pytest.mark.parametrize("value", [-1, 0, 1])
def test_no_nan_for_min_max_values(value, parameter_name):
    kwargs = {"allow_nan": False, parameter_name: value}

    @given(ds.floats(**kwargs))
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
@given(data=ds.data())
def test_data_explicitly_rejects_non_strategies(data, value, label):
    with pytest.raises(InvalidArgument):
        data.draw(value, label=label)


@given(ds.integers().filter(bool).filter(lambda x: x % 3))
def test_chained_filter(x):
    assert x and x % 3


def test_chained_filter_tracks_all_conditions():
    s = ds.integers().filter(bool).filter(lambda x: x % 3)
    assert len(s.wrapped_strategy.flat_conditions) == 2


@pytest.mark.parametrize("version", [4, 6])
@given(data=ds.data())
def test_ipaddress_from_network_is_always_correct_version(data, version):
    ip = data.draw(ds.ip_addresses(v=version), label="address")
    assert ip.version == version


@given(data=ds.data(), network=ds.from_type(IPv4Network) | ds.from_type(IPv6Network))
def test_ipaddress_from_network_is_always_in_network(data, network):
    ip = data.draw(ds.ip_addresses(network=network), label="address")
    assert ip in network
    assert ip.version == network.version


class AnEnum(enum.Enum):
    a = 1


def requires_arg(value):
    """Similar to the enum.Enum.__call__ method."""


@given(ds.data())
def test_builds_error_messages(data):
    # If we call them directly, we get a simple TypeError in both cases
    with pytest.raises(TypeError):
        requires_arg()
    with pytest.raises(TypeError):
        AnEnum()
    # But we have an improved error message if you try to build an Enum
    assert issubclass(InvalidArgument, TypeError)  # it's a valid substitution
    with pytest.raises(TypeError):  # which only applies to enums
        data.draw(ds.builds(requires_arg))
    with pytest.raises(
        InvalidArgument,
        match=r".* try using sampled_from\(.+\) instead of builds\(.+\)",
    ):
        data.draw(ds.builds(AnEnum))
    # and sampled_from() does in fact work
    data.draw(ds.sampled_from(AnEnum))
