===========
Ghostwriter
===========

.. automodule:: hypothesis.extra.ghostwriter
   :members:

A note for test-generation researchers
--------------------------------------

Ghostwritten tests are intended as a *starting point for human authorship*,
to demonstrate best practice, help novices past blank-page paralysis, and save time
for experts.  They *may* be ready-to-run, or include placeholders and ``# TODO:``
comments to fill in strategies for unknown types.  In either case, improving tests
for their own code gives users a well-scoped and immediately rewarding context in
which to explore property-based testing.

By contrast, most test-generation tools aim to produce ready-to-run test suites...
and implicitly assume that the current behavior is the desired behavior.
However, the code might contain bugs, and we want our tests to fail if it does!
Worse, tools require that the code to be tested is finished and executable,
making it impossible to generate tests as part of the development process.

`Fraser 2013`_ found that evolving a high-coverage test suite (e.g. Randoop_, EvoSuite_, Pynguin_)
"leads to clear improvements in commonly applied quality metrics such as code coverage
[but] no measurable improvement in the number of bugs actually found by developers"
and that "generating a set of test cases, even high coverage test cases,
does not necessarily improve our ability to test software".
Invariant detection (famously Daikon_; in PBT see e.g. `Alonso 2022`_,
QuickSpec_, Speculate_) relies on code execution. Program slicing (e.g. FUDGE_,
FuzzGen_, WINNIE_) requires downstream consumers of the code to test.

Ghostwriter inspects the function name, argument names and types, and docstrings.
It can be used on buggy or incomplete code, runs in a few seconds, and produces
a single semantically-meaningful test per function or group of functions.
Rather than detecting regressions, these tests check semantic properties such as
`encode/decode or save/load round-trips <https://zhd.dev/ghostwriter/?q=gzip.compress>`__,
for `commutative, associative, and distributive operations
<https://zhd.dev/ghostwriter/?q=operator.mul>`__,
`equivalence between methods <https://zhd.dev/ghostwriter/?q=operator.add+numpy.add>`__,
`array shapes <https://zhd.dev/ghostwriter/?q=numpy.matmul>`__,
and idempotence.  Where no property is detected, we simply check for
'no error on valid input' and allow the user to supply their own invariants.

Evaluations such as the SBFT24_ competition_ measure performance on a task which
the Ghostwriter is not intended to perform.  I'd love to see qualitative user
studies, such as `PBT in Practice`_ for test generation, which could check
whether the Ghostwriter is onto something or tilting at windmills.
If you're interested in similar questions, `drop me an email`_!

.. _Daikon: https://plse.cs.washington.edu/daikon/pubs/
.. _Alonso 2022: https://doi.org/10.1145/3540250.3559080
.. _QuickSpec: http://www.cse.chalmers.se/~nicsma/papers/quickspec2.pdf
.. _Speculate: https://matela.com.br/speculate.pdf
.. _FUDGE: https://research.google/pubs/pub48314/
.. _FuzzGen: https://www.usenix.org/conference/usenixsecurity20/presentation/ispoglou
.. _WINNIE: https://www.ndss-symposium.org/wp-content/uploads/2021-334-paper.pdf
.. _Fraser 2013: https://doi.org/10.1145/2483760.2483774
.. _Randoop: https://homes.cs.washington.edu/~mernst/pubs/feedback-testgen-icse2007.pdf
.. _EvoSuite: https://www.evosuite.org/wp-content/papercite-data/pdf/esecfse11.pdf
.. _Pynguin: https://arxiv.org/abs/2007.14049
.. _SBFT24: https://arxiv.org/abs/2401.15189
.. _competition: https://github.com/ThunderKey/python-tool-competition-2024
.. _PBT in Practice: https://harrisongoldste.in/papers/icse24-pbt-in-practice.pdf
.. _drop me an email: mailto:zac@zhd.dev?subject=Hypothesis%20Ghostwriter%20research
