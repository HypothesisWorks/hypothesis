import hypothesis.strategytable as st
import hypothesis.searchstrategy as strat
import hypothesis.descriptors as descriptors


def test_strategies_can_be_used_in_descriptors():
    intxfloat = st.StrategyTable.default().strategy((
        int, strat.ExponentialFloatStrategy()
    ))
    assert intxfloat.descriptor == (int, float)


def test_has_strategy_for_frozensets():
    assert (
        st.StrategyTable.default().strategy(frozenset([int])).descriptor ==
        frozenset([int]))


def test_has_strategy_for_samples():
    table = st.StrategyTable.default()
    sampling = descriptors.sampled_from([1, 2, 3])
    assert table.has_specification_for(sampling)
    assert table.has_specification_for([sampling])
    assert table.has_specification_for(set([sampling]))
