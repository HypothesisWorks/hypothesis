# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from hypothesis.internal.conjecture.dfa import DFA
from hypothesis.internal.conjecture.junkdrawer import find_integer

"""
This module contains an implementation of the L* algorithm
for learning a deterministic finite automaton based on an
unknown membership function and a series of examples of
strings that may or may not satisfy it.

The two relevant papers for understanding this are:

* Angluin, Dana. "Learning regular sets from queries and counterexamples."
  Information and computation 75.2 (1987): 87-106.
* Rivest, Ronald L., and Robert E. Schapire. "Inference of finite automata
  using homing sequences." Information and Computation 103.2 (1993): 299-347.
  Note that we only use the material from section 4.5 "Improving Angluin's L*
  algorithm" (page 318), and all of the rest of the material on homing
  sequences can be skipped.

The former explains the core algorithm, the latter a modification
we use (which we have further modified) which allows it to
be implemented more efficiently.

We have two major departures from the paper:

1. We learn the automaton lazily as we traverse it. This is particularly
   valuable because if we make many corrections on the same string we only
   have to learn the transitions that correspond to the string we are
   correcting on.
2. We make use of our ``find_integer`` method rather than a binary search
   as proposed in the Rivest and Schapire paper, as we expect that
   usually most strings will be mispredicted near the beginning.

A note on performance: This code is not really fast enough for
us to ever want to run in production on large strings, and this
is somewhat intrinsic. We should only use it in testing or for
learning languages offline that we can record for later use.

"""


class LStar:
    def __init__(self, member):
        self.__experiments = []
        self.__cache = {}
        self.__member = member

        self.__add_experiment(b"")

    def member(self, s):
        """Check whether this string is a member of the language
        to be learned."""
        s = bytes(s)
        try:
            return self.__cache[s]
        except KeyError:
            return self.__cache.setdefault(s, self.__member(s))

    @property
    def generation(self):
        """Return an integer value that will be incremented
        every time the DFA we predict changes."""
        return len(self.__experiments)

    @property
    def dfa(self):
        """Returns our current model of a DFA for matching
        the language we are learning."""
        if self.__dfa is None:
            self.__dfa = ExperimentDFA(self.member, self.__experiments)
        return self.__dfa

    def learn(self, s):
        """Learn to give the correct answer on this string.
        That is, after this method completes we will have
        ``self.dfa.matches(s) == self.member(s)``.

        Note that we do not guarantee that this will remain
        true in the event that learn is called again with
        a different string. It is in principle possible that
        future learning will cause us to make a mistake on
        this string. However, repeatedly calling learn on
        each of a set of strings until the generation stops
        changing is guaranteed to terminate.
        """
        s = bytes(s)
        correct_outcome = self.member(s)

        # We don't want to check this inside the loop because it potentially
        # causes us to evaluate more of the states than we actually need to,
        # but if our model is mostly correct then this will be faster because
        # we only need to evaluate strings that are of the form
        # ``state + experiment``, which will generally be cached and/or needed
        # later.
        if self.dfa.matches(s) == correct_outcome:
            return

        # In the papers they assume that we only run this process
        # once, but this is silly - often when you've got a messy
        # string it will be wrong for many different reasons.
        #
        # Thus we iterate this to a fixed point where we repair
        # the DFA by repeatedly adding experiments until the DFA
        # agrees with the membership function on this string.
        while True:
            dfa = self.dfa

            states = [dfa.start]

            def seems_right(n):
                """After reading n characters from s, do we seem to be
                in the right state?

                We determine this by replacing the first n characters
                of s with the label of the state we expect to be in.
                If we are in the right state, that will replace a substring
                with an equivalent one so must produce the same answer.
                """
                if n > len(s):
                    return False

                # Populate enough of the states list to know where we are.
                while n >= len(states):
                    states.append(dfa.transition(states[-1], s[len(states) - 1]))

                return self.member(dfa.label(states[n]) + s[n:]) == correct_outcome

            n = find_integer(seems_right)

            # We got to the end without ever finding ourself in a bad
            # state, so we must correctly match this string.
            if n == len(s):
                assert dfa.matches(s) == correct_outcome
                break

            # Reading n characters does not put us in a bad state but
            # reading n + 1 does. This means that the remainder of
            # the string that we have not read yet is an experiment
            # that allows us to distinguish the state that we ended
            # up in from the state that we should have ended up in.
            self.__add_experiment(s[n + 1 :])

    def __add_experiment(self, e):
        self.__experiments.append(e)
        self.__dfa = None


class ExperimentDFA(DFA):
    """This implements a lazily calculated DFA where states
    are labelled by some string that reaches them, and are
    distinguished by a membership test and a set of experiments."""

    def __init__(self, member, experiments):
        DFA.__init__(self)
        self.__experiments = tuple(experiments)
        self.__member = member

        self.__states = [b""]
        self.__rows_to_states = {tuple(map(member, experiments)): 0}
        self.__transition_cache = {}

    def label(self, i):
        return self.__states[i]

    @property
    def start(self):
        return 0

    def is_accepting(self, i):
        return self.__member(self.__states[i])

    def transition(self, i, c):
        key = (i, c)
        try:
            return self.__transition_cache[key]
        except KeyError:
            pass
        s = self.__states[i]

        # t is either the string that labels our destination
        # state or one equivalent to it.
        t = s + bytes([c])

        # A row is a tuple of booleans that corresponds to
        # the information our experiments can reveal about
        # this string. Two strings with different rows *must*
        # correspond to different states in the DFA for our
        # membership function, because the same path out
        # of them (taken by one of the experiments) leads to
        # different results.
        row = tuple(self.__member(t + e) for e in self.__experiments)
        try:
            # If we have seen this row before, assume that this
            # state is equivalent to that already discovered one.
            # If it is not, we will have to find a new experiment
            # to reveal that,
            result = self.__rows_to_states[row]
        except KeyError:
            # This string is definitely not equivalent to any of
            # those visited before, so it must be a new state and
            # we add it to our list of states.
            result = len(self.__states)
            self.__states.append(t)
            self.__rows_to_states[row] = result
        self.__transition_cache[key] = result
        return result
