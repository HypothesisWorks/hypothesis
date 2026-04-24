# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Stateful test that a program replayed through a deferred printer
produces the same output as when applied directly."""

from dataclasses import dataclass

from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule
from hypothesis.vendor import pretty


# --- AST for printing programs ----------------------------------------


@dataclass(frozen=True, slots=True)
class PText:
    s: str

    def apply(self, p):
        p.text(self.s)


@dataclass(frozen=True, slots=True)
class PBreakable:
    sep: str

    def apply(self, p):
        p.breakable(self.sep)


@dataclass(frozen=True, slots=True)
class PBreak:
    def apply(self, p):
        p.break_()


@dataclass(frozen=True, slots=True)
class PGroup:
    indent: int
    open: str
    close: str
    children: tuple

    def apply(self, p):
        with p.group(self.indent, self.open, self.close):
            for c in self.children:
                c.apply(p)


@dataclass(frozen=True, slots=True)
class PIndent:
    amount: int
    children: tuple

    def apply(self, p):
        with p.indent(self.amount):
            for c in self.children:
                c.apply(p)


@dataclass(frozen=True, slots=True)
class PProgram:
    """A sequence of printing operations forming a single program."""

    ops: tuple

    def apply(self, p):
        for op in self.ops:
            op.apply(p)


# --- Strategies -------------------------------------------------------

# Keep alphabets small so line-wrap decisions are reachable without huge inputs.
small_text = st.text(alphabet="ab \n", max_size=6)
short_sep = st.text(alphabet="  \n", max_size=2)

leaf_op = st.one_of(
    small_text.map(PText),
    short_sep.map(PBreakable),
    st.just(PBreak()),
)


def _container(children_strategy):
    return st.one_of(
        st.builds(
            PGroup,
            indent=st.integers(0, 4),
            open=small_text,
            close=small_text,
            children=st.lists(children_strategy, max_size=4).map(tuple),
        ),
        st.builds(
            PIndent,
            amount=st.integers(0, 4),
            children=st.lists(children_strategy, max_size=4).map(tuple),
        ),
    )


op_strategy = st.recursive(
    leaf_op,
    lambda children: st.one_of(children, _container(children)),
    max_leaves=10,
)

program_strategy = st.lists(op_strategy, max_size=4).map(tuple).map(PProgram)


# --- Bundle entry -----------------------------------------------------


class _DeferredEntry:
    """Tracks a deferred printer and the list of programs remaining to
    apply to it during the stateful run."""

    def __init__(self, deferred, programs):
        self.deferred = deferred
        self.remaining = list(programs)


# --- Stateful test ----------------------------------------------------


class DeferredPrinterAgreement(RuleBasedStateMachine):
    """Asserts that applying a sequence of printing programs directly to
    one printer produces the same output as using deferred()/finalize()
    on another, where the programs are applied through the deferred."""

    def __init__(self):
        super().__init__()
        self.model_printer = pretty.RepresentationPrinter()
        self.test_printer = pretty.RepresentationPrinter()
        # All deferred entries ever created, kept in creation order so we
        # can flush any leftover programs during teardown.
        self.entries = []

    deferreds = Bundle("deferreds")

    @rule(program=program_strategy)
    def apply_print_program(self, program):
        program.apply(self.model_printer)
        program.apply(self.test_printer)

    @rule(
        target=deferreds,
        programs=st.lists(program_strategy, min_size=1, max_size=4),
    )
    def defer_print_programs(self, programs):
        # Apply everything to the model immediately (no deferral there).
        for prog in programs:
            prog.apply(self.model_printer)
        # On the test side, open a deferred and queue the same programs
        # to be applied to it (some now, the rest during teardown).
        deferred = self.test_printer.deferred()
        entry = _DeferredEntry(deferred, programs)
        self.entries.append(entry)
        return entry

    @rule(entry=deferreds)
    def run_deferred_print(self, entry):
        if entry.remaining:
            prog = entry.remaining.pop(0)
            prog.apply(entry.deferred)

    def teardown(self):
        # Flush any leftover programs onto their deferreds in creation order.
        for entry in self.entries:
            while entry.remaining:
                prog = entry.remaining.pop(0)
                prog.apply(entry.deferred)
        if self.entries:
            self.test_printer.finalize()
        assert self.model_printer.getvalue() == self.test_printer.getvalue()


TestDeferredPrinterAgreement = DeferredPrinterAgreement.TestCase
