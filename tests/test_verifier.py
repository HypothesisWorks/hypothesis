from hypothesis import Verifier
from hypothesis.settings import Settings
from random import Random
import pytest


def test_verifier_explodes_when_you_mix_random_and_derandom():
    settings = Settings(derandomize=True)
    with pytest.raises(ValueError):
        Verifier(settings=settings, random=Random())
