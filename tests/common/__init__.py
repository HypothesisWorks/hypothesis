from hypothesis import Verifier
import hypothesis.settings as hs
from hypothesis.strategytable import StrategyTable
import hypothesis.searchstrategy as strat


settings = hs.Settings(max_examples=100, timeout=4)
small_table = StrategyTable()

small_table.define_specification_for_instances(
    list,
    lambda strategies, descriptor:
        strat.ListStrategy(
            list(map(strategies.strategy, descriptor)),
            average_length=2.0
        )
)


small_verifier = Verifier(
    settings=settings,
    strategy_table=small_table,
)
