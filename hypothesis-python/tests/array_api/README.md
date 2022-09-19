This folder contains tests for `hypothesis.extra.array_api`.

## Running against different array modules

By default it will run against `numpy.array_api`. If that's not available
(likely because an older NumPy version is installed), these tests will fallback
to using the mock defined at the bottom of `src/hypothesis/extra/array_api.py`.

You can test other array modules which adopt the Array API via the
`HYPOTHESIS_TEST_ARRAY_API` environment variable. There are two recognized
options:

* `"default"`: uses the mock, and `numpy.array_api` if available.
* `"all"`: uses all array modules found via entry points, _and_ the mock.

If neither of these, the test suite will then try resolve the variable like so:

1. If the variable matches a name of an available entry point, load said entry point.
2. If the variables matches a valid import path, import said path.

For example, to specify NumPy's Array API implementation, you could use its
entry point (**1.**),

    HYPOTHESIS_TEST_ARRAY_API=numpy pytest tests/array_api

or use the import path (**2.**),

    HYPOTHESIS_TEST_ARRAY_API=numpy.array_api pytest tests/array_api

The former method is more ergonomic, but as entry points are optional for
adopting the Array API, you will need to use the latter method for libraries
that opt-out.
