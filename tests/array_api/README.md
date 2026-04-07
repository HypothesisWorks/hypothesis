This folder contains tests for `hypothesis.extra.array_api`.

## Mocked array module

A mock of the Array API namespace exists as `mock_xp` in `extra.array_api`. This
wraps NumPy-proper to conform it to the *draft* spec, where `array_api_strict`
might not. This is not a fully compliant wrapper, but conforms enough for the
purposes of testing.

## Running against different array modules

You can test other array modules which adopt the Array API via the
`HYPOTHESIS_TEST_ARRAY_API` environment variable. There are two recognized
options:

* `"default"`: uses the mock.
* `"all"`: uses all array modules found via entry points, _and_ the mock.

If neither of these, the test suite will then try resolve the variable like so:

1. If the variable matches a name of an available entry point, load said entry point.
2. If the variables matches a valid import path, import said path.

For example, to specify NumPy's Array API implementation[^1], you could use its
entry point (**1.**),

    HYPOTHESIS_TEST_ARRAY_API=numpy pytest tests/array_api

or use the import path (**2.**),

    HYPOTHESIS_TEST_ARRAY_API=numpy.array_api pytest tests/array_api

The former method is more ergonomic, but as entry points are optional for
adopting the Array API, you will need to use the latter method for libraries
that opt-out.

## Running against different API versions

You can specify the `api_version` to use when testing array modules via the 
`HYPOTHESIS_TEST_ARRAY_API_VERSION` environment variable. There is one
recognized option:

* `"default"`: infers the latest API version for each array module.

Otherwise the test suite will use the variable as the `api_version` argument for
`make_strategies_namespace()`.

In the future we intend to support running tests against multiple API versioned
namespaces, likely with an additional recognized option that infers all
supported versions.

[^1]: Note NumPy will likely remove `numpy.array_api` in the future ([NEP 56](https://github.com/numpy/numpy/pull/25542))
in favour of the third-party [`array-api-strict`](https://github.com/data-apis/array-api-strict) library.