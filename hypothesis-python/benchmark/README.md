This directory contains plotting code for our shrinker benchmarking. The code for collecting the data is in `conftest.py`. This directory handles plotting the results.

The plotting script (but not collecting benchmark data) requires additional dependencies: `pip install scipy vl-convert-python`.

To run a benchmark:

- `pytest tests/ --hypothesis-benchmark-shrinks new --hypothesis-benchmark-output data.json` (starting on the newer version)
- `pytest tests/ --hypothesis-benchmark-shrinks old --hypothesis-benchmark-output data.json` (after switching to the old version)
  - Use the same `data.json` path, the benchmark will append data. You can append `-k ...` for both commands to subset the benchmark.
- `python benchmark/graph.py data.json shrinking.png`

This hooks any `minimal()` calls any reports the number of shrinks. Default (and currently unchangeable) number of iterations is 5 per test.
