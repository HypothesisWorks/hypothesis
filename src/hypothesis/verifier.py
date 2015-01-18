"""
The main entry point for Hypothesis, providing the falsify method and all
the various errors it may throw.
"""

from hypothesis.strategytable import StrategyTable
from random import Random
import time
from hypothesis.internal.compat import hrange
import hypothesis.settings as hs
from hypothesis.internal.utils.reflection import (
    get_pretty_function_description, function_digest
)
from hypothesis.internal.tracker import Tracker


def assume(condition):
    """
    Assert a precondition for this test. If this is not truthy then the
    test will abort but not fail and Hypothesis will make a "best effort"
    attempt to avoid similar examples in future.
    """
    if not condition:
        raise UnsatisfiedAssumption()


class Verifier(object):
    """
    A wrapper object holding state required for a falsify invocation.
    """
    def __init__(
            self,
            strategy_table=None,
            random=None,
            settings=None,
    ):
        if settings is None:
            settings = hs.default
        self.strategy_table = strategy_table or StrategyTable()
        self.min_satisfying_examples = settings.min_satisfying_examples
        self.max_skipped_examples = settings.max_skipped_examples
        self.max_examples = settings.max_examples
        self.timeout = settings.timeout
        if settings.derandomize and random:
            raise ValueError(
                "A verifier cannot both be derandomized and have a random "
                "generator")

        if settings.derandomize:
            self.random = None
        else:
            self.random = random or Random()
        self.max_regenerations = 0

    def falsify(
            self, hypothesis, *argument_types
    ):  # pylint: disable=too-many-locals,too-many-branches
        """
        Attempt to construct an example tuple x matching argument_types such
        that hypothesis(*x) returns a falsey value or throws an AssertionError
        """
        random = self.random
        if random is None:
            random = Random(
                function_digest(hypothesis)
            )

        search_strategy = (
            self.strategy_table.specification_for(argument_types))

        def falsifies(args):  # pylint: disable=missing-docstring
            try:
                return not hypothesis(*search_strategy.copy(args))
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                return False

        falsifying_examples = []
        examples_found = 0
        satisfying_examples = 0
        timed_out = False
        if argument_types:
            max_examples = self.max_examples
            min_satisfying_examples = self.min_satisfying_examples
            parameter_values = max(2, int(float(max_examples) / 5))
        else:
            max_examples = 1
            min_satisfying_examples = 1
            parameter_values = 1

        parameter_values = [
            search_strategy.parameter.draw(random)
            for _ in hrange(parameter_values)
        ]

        accepted_examples = [0] * max_examples
        rejected_examples = [0] * max_examples
        track_seen = Tracker()

        start_time = time.time()

        def time_to_call_it_a_day():
            """Have we exceeded our timeout?"""
            return time.time() >= start_time + self.timeout

        initial_run = 0
        skipped_examples = 0

        while not (
                examples_found >= max_examples or
                len(falsifying_examples) >= 1
        ):
            if time_to_call_it_a_day():
                break

            if initial_run < len(parameter_values):
                i = initial_run
                initial_run += 1
            else:
                i = max(
                    hrange(len(parameter_values)),
                    key=lambda k: random.betavariate(
                        accepted_examples[k] + 1, rejected_examples[k] + 1
                    )
                )
            parameter = parameter_values[i]

            args = search_strategy.produce(random, parameter)
            assert search_strategy.could_have_produced(args)

            if track_seen.track(args) > 1:
                rejected_examples[i] += 1
                skipped_examples += 1
                if skipped_examples >= self.max_skipped_examples:
                    raise Exhausted(hypothesis, examples_found)
                else:
                    # This really is covered. I suspect a bug in coverage that
                    # I have not yet narrowed down. It is impossible to execute
                    # the other branch without first executing this one and
                    # there is a test that cannot pass without executing the
                    # other branch.
                    continue  # pragma: no cover
            else:
                skipped_examples = 0
            examples_found += 1
            try:
                is_falsifying_example = not hypothesis(
                    *search_strategy.copy(args))
            except AssertionError:
                is_falsifying_example = True
            except UnsatisfiedAssumption:
                rejected_examples[i] += 1
                continue
            accepted_examples[i] += 1
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)
        run_time = time.time() - start_time
        timed_out = run_time >= self.timeout

        if not falsifying_examples:
            if satisfying_examples < min_satisfying_examples:
                raise Unsatisfiable(hypothesis, satisfying_examples, run_time)
            elif timed_out:
                raise Timeout(hypothesis, satisfying_examples, run_time)
            else:
                raise Unfalsifiable(hypothesis)

        for example in falsifying_examples:
            if not falsifies(example):
                raise Flaky(hypothesis, example)

        best_example = falsifying_examples[0]

        for simpler in search_strategy.simplify_such_that(
                best_example, falsifies
        ):
            best_example = simpler
            if time_to_call_it_a_day():
                break

        return best_example


def falsify(*args, **kwargs):
    """
    A convenience wrapper function for Verifier.falsify
    """
    return Verifier(**kwargs).falsify(*args)


class HypothesisException(Exception):
    """
    Generic parent class for exceptions thrown by Hypothesis
    """
    pass


class UnsatisfiedAssumption(HypothesisException):
    """
    An internal error raised by assume. If you're seeing this error something
    has gone wrong.
    """

    def __init__(self):
        super(UnsatisfiedAssumption, self).__init__('Unsatisfied assumption')


class Unfalsifiable(HypothesisException):
    """
    The hypothesis we have been asked to falsify appears to be always true.
    This does not guarantee that no counter-example exists, only that we
    were unable to find one.
    """

    def __init__(self, hypothesis, extra=''):
        super(Unfalsifiable, self).__init__(
            'Unable to falsify hypothesis %s%s' % (
                get_pretty_function_description(hypothesis), extra)
        )


class Exhausted(Unfalsifiable):
    """
    We appear to have considered the entire example space available before we
    ran out of time or number of examples. This does not guarantee that we have
    considered the whole example space (it could just be a bad search strategy)
    but it makes it pretty likely that this hypothesis is just always true.
    """
    def __init__(self, hypothesis, n_examples):
        super(Exhausted, self).__init__(
            hypothesis, " exhausted parameter space after %d examples" % (
                n_examples,
            )
        )


class Unsatisfiable(HypothesisException):
    """
    We ran out of time or examples before we could find enough examples which
    satisfy the assumptions of this hypothesis. This could be because the
    function is too slow. If so, try upping the timeout. It could also be
    because the function is using assume in a way that is too hard to satisfy.
    If so, try writing a custom strategy or using a better starting point (e.g
    if you are requiring a list has unique values you could instead filter out
    all duplicate values from the list)
    """

    def __init__(self, hypothesis, examples, run_time):
        super(Unsatisfiable, self).__init__((
            'Unable to satisfy assumptions of hypothesis %s. ' +
            'Only %s examples found after %g seconds'
            ) % (
                get_pretty_function_description(hypothesis),
                str(examples),
                run_time))


class Flaky(HypothesisException):
    """
    This function appears to fail non-deterministically: We have seen it fail
    when passed this example at least once, but a subsequent invocation did not
    fail.

    Common causes for this problem are:
        1. The function depends on external state. e.g. it uses an external
           random number generator. Try to make a version that passes all the
           relevant state in from Hypothesis.
        2. The function is suffering from too much recursion and its failure
           depends sensitively on where it's been called from.
        3. The function is timing sensitive and can fail or pass depending on
           how long it takes. Try breaking it up into smaller functions which
           dont' do that and testing those instead.
    """
    def __init__(self, hypothesis, example):
        super(Flaky, self).__init__((
            "Hypothesis %r produces unreliable results: %r falsified it on the"
            " first call but did not on a subsequent one"
        ) % (get_pretty_function_description(hypothesis), example))


class Timeout(Unfalsifiable):
    """
    We were unable to find enough examples that satisfied the preconditions of
    this hypothesis in the amount of time allotted to us.
    """
    def __init__(self, hypothesis, satisfying_examples, run_time):
        super(Timeout, self).__init__(
            hypothesis,
            ' after %gs (considered %d examples)' % (
                run_time, satisfying_examples)
        )
