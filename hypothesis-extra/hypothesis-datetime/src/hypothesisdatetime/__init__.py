from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import SearchStrategy
from datetime import datetime, MINYEAR, MAXYEAR
import hypothesis.params as params


def draw_day_for_month(random, year, month):
    while True:
        day = random.randint(1, 31)
        try:
            datetime(
                year=year, month=month, day=day
            )
            return day
        except ValueError as e:
            if e.args[0] != 'day is out of range for month':
                raise e


def maybe_zero_or(random, p, v):
    if random.random() <= p:
        return v
    else:
        return 0


class DatetimeStrategy(SearchStrategy):
    descriptor = datetime
    parameter = params.CompositeParameter(
        p_hour=params.UniformFloatParameter(0, 1),
        p_minute=params.UniformFloatParameter(0, 1),
        p_second=params.UniformFloatParameter(0, 1),
        month=params.NonEmptySubset(list(range(1, 13))),
    )

    def produce(self, random, pv):
        year = random.randint(MINYEAR, MAXYEAR)
        month = random.choice(pv.month)
        return datetime(
            year=year,
            month=month,
            day=draw_day_for_month(random, year, month),
            hour=maybe_zero_or(random, pv.p_hour, random.randint(0, 23)),
            minute=maybe_zero_or(random, pv.p_minute, random.randint(0, 59)),
            second=maybe_zero_or(random, pv.p_second, random.randint(0, 59)),
            microsecond=random.randint(0, 1000000-1),
        )


def load():
    StrategyTable.default().define_specification_for(
        datetime, lambda s, d: DatetimeStrategy()
    )
