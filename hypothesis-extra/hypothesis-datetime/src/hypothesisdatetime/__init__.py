from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import SearchStrategy
from datetime import datetime, MINYEAR, MAXYEAR
import hypothesis.params as params
from hypothesis.internal.compat import hrange


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

    def simplify(self, value):
        s = {value}
        s.add(value.replace(microsecond=0))
        s.add(value.replace(second=0))
        s.add(value.replace(minute=0))
        s.add(value.replace(hour=0))
        s.add(value.replace(day=1))
        s.add(value.replace(month=1))
        s.remove(value)
        for t in s:
            yield t
        year = value.year
        if year == 2000:
            return
        # We swallow a bunch of value errors here.
        # These can happen if the original value was february 29 on a
        # leap year and the current year is not a leap year.
        try:
            yield value.replace(year=2000)
        except ValueError:
            pass
        mid = (year + 2000) // 2
        if mid != 2000 and mid != year:
            try:
                yield value.replace(year=mid)
            except ValueError:
                pass
        years = hrange(year, 2000, -1 if year > 2000 else 1)
        for year in years:
            if year == mid:
                continue
            try:
                yield value.replace(year)
            except ValueError:
                pass


def load():
    StrategyTable.default().define_specification_for(
        datetime, lambda s, d: DatetimeStrategy()
    )
