import random
from hypothesisdatetime import draw_day_for_month
import pytest


def test_draw_day_for_month_errors_on_bad_month():
    with pytest.raises(ValueError):
        draw_day_for_month(random, 2001, 13)
