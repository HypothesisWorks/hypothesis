import pytest

from hypothesis import Phase, given, settings, strategies as st


@pytest.fixture(params=[10, 100])
def _vary_max_examples(request):
    settings.register_profile("_max_examples_fixture", settings(max_examples=request.param))
    settings.load_profile("_max_examples_fixture")
    yield
    settings.load_profile("default")


def test_integers_generation(bench, _vary_max_examples):

    @given(st.integers())
    @settings(database=None, phases=[Phase.generate])
    def test(x):
        pass

    bench(test)


def test_integers_shrink(bench):

    @given(st.integers(min_value=0))
    @settings(database=None, phases=[Phase.generate, Phase.shrink], max_examples=50)
    def test(x):
        assert x < 10

    bench(test, exc=AssertionError)


def test_unique_lists_sampled_from(bench, _vary_max_examples):

    @given(st.lists(st.sampled_from(range(2048)), unique=True))
    @settings(database=None, phases=[Phase.generate])
    def test(x):
        pass

    bench(test)


def test_fixed_dictionaries_generate(bench, _vary_max_examples):  # adapted from #4014

    @given(st.fixed_dictionaries(
        {
            "fingerprints": st.fixed_dictionaries(
                {
                    key: st.dictionaries(st.integers(min_value=0, max_value=0x800),
                                         st.integers(min_value=0, max_value=64))
                    for key in range(8)
                }
            ),
        }
    ))
    @settings(database=None, phases=[Phase.generate])
    def test(x):
        pass

    bench(test)


def test_dictionaries_generate(bench, _vary_max_examples):

    @given(st.dictionaries(st.integers(min_value=0, max_value=2048),
                           st.integers(min_value=0, max_value=64)))
    @settings(database=None, phases=[Phase.generate])
    def test(x):
        pass

    bench(test)
