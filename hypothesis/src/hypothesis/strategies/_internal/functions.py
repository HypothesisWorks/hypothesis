# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import Parameter, Signature
from weakref import WeakKeyDictionary

from hypothesis.control import note, should_note
from hypothesis.errors import InvalidState
from hypothesis.internal.reflection import (
    convert_positional_arguments,
    get_signature,
    nicerepr,
    proxies,
    repr_call,
)
from hypothesis.strategies._internal.lazy import unwrap_strategies
from hypothesis.strategies._internal.strategies import (
    RecurT,
    SampledFromStrategy,
    SearchStrategy,
)
from hypothesis.utils.conventions import UniqueIdentifier

can_vary = UniqueIdentifier("can_vary")


class FunctionStrategy(SearchStrategy):
    def __init__(self, like, returns, pure):
        super().__init__()
        self.like = like
        self.returns = returns
        self.pure = pure
        # If `returns` can only generate a single value - just(), none(), or a
        # one-element sampled_from() - we know what our functions return before
        # they are ever called, and show them as constant lambdas instead. We
        # have to unwrap lazy wrappers to see that, and to bail out if any
        # .map() or .filter() was applied, since those transformations could
        # change or reject the value we'd otherwise report.
        unwrapped = unwrap_strategies(returns)
        if (
            isinstance(unwrapped, SampledFromStrategy)
            and len(unwrapped.elements) == 1
            and not unwrapped._transformations
        ):
            self._constant = unwrapped.elements[0]
        else:
            self._constant = can_vary
        # Using wekrefs-to-generated-functions means that the cache can be
        # garbage-collected at the end of each example, reducing memory use.
        self._cache = WeakKeyDictionary()

    def _pretty_constant_function(self, p, cycle):
        # Annotations are valid in a signature, but not in a lambda.
        sig = get_signature(self.like, follow_wrapped=False)
        params = str(
            sig.replace(
                parameters=[
                    param.replace(annotation=Parameter.empty)
                    for param in sig.parameters.values()
                ],
                return_annotation=Signature.empty,
            )
        )[1:-1]
        p.text(f"lambda {params}: " if params else "lambda: ")
        p.pretty(self._constant)

    def calc_is_empty(self, recur: RecurT) -> bool:
        return recur(self.returns)

    def do_draw(self, data):
        # If we know what the function returns, we show it as a constant lambda
        # instead of noting every call - the notes would be redundant.
        varies = self._constant is can_vary

        @proxies(self.like)
        def inner(*args, **kwargs):
            if data.frozen:
                raise InvalidState(
                    f"This generated {nicerepr(self.like)} function can only "
                    "be called within the scope of the @given that created it."
                )
            if self.pure:
                args, kwargs = convert_positional_arguments(self.like, args, kwargs)
                key = (args, frozenset(kwargs.items()))
                cache = self._cache.setdefault(inner, {})
                if key not in cache:
                    cache[key] = data.draw(self.returns)
                    # optimization to avoid needless repr_call
                    if varies and should_note():
                        rep = repr_call(self.like, args, kwargs, reorder=False)
                        note(f"Called function: {rep} -> {cache[key]!r}")
                return cache[key]
            else:
                val = data.draw(self.returns)
                if varies and should_note():
                    rep = repr_call(self.like, args, kwargs, reorder=False)
                    note(f"Called function: {rep} -> {val!r}")
                return val

        if not varies:
            inner._repr_pretty_ = self._pretty_constant_function
        return inner
