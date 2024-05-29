This directory contains code for benchmarking Hypothesis' shrinking. This was written for [pull/3962](https://github.com/HypothesisWorks/hypothesis/pull/3962) and is a manual process at the moment, though we may eventually integrate it more closely with ci for automated benchmarking.

To run a benchmark:

* Add the contents of `conftest.py` to the bottom of `hypothesis-python/tests/conftest.py`
* In `hypothesis-python/tests/common/debug.py`, change `derandomize=True` to `derandomize=False` (if you are running more than one trial)
* Run the tests: `pytest hypothesis-python/tests/`
  * Note that the benchmarking script does not currently support xdist, so do not use `-n 8` or similar.

When pytest finishes the output will contain a dictionary of the benchmarking results. Add that as a new entry in `data.json`. Repeat for however many trials you want; n=5 seems reasonable.

Also repeat for both your baseline ("old") and your comparison ("new") code.

Then run `python graph.py` to generate a graph comparing the old and new results.
