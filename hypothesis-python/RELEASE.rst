RELEASE_TYPE: minor

This release adds a :ref:`.hypothesis.fuzz_one_input <fuzz_one_input>`
attribute to :func:`@given <hypothesis.given>` tests, for easy integration
with external fuzzers such as `python-afl <https://github.com/jwilk/python-afl>`__
(supporting :issue:`171`).
