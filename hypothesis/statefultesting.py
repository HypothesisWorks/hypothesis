from functools import wraps
from random import choice
from hypothesis.verifier import Verifier
import hypothesis

def step(f):
    f.hypothesis_test_step = True
    return f

def integrity_test(f):
    f.hypothesis_integrity_tests = True
    return f


class PreconditionNotMet(Exception):
    def __init__(self):
        Exception.__init__(self, "Precondition not met")

def precondition(t):
    if not t: raise PreconditionNotMet()

class StatefulTest:
    @classmethod
    def test_steps(cls):
        return cls.functions_with_attributes('hypothesis_test_step')
    
    @classmethod
    def integrity_tests(cls):
        return cls.functions_with_attributes('hypothesis_integrity_tests')

    @classmethod
    def functions_with_attributes(cls, attr):
        return [v for v in cls.__dict__.values() if hasattr(v, attr)]
        
    @classmethod
    def produce_step(cls, producers, size):
        return choice(cls.test_steps())

    @classmethod
    def run_sequence(cls, steps):
        value = cls()
        for s in steps:
            try:
                s(value)
            except PreconditionNotMet:
                pass
        return True

    @classmethod
    def breaking_example(cls):
       return hypothesis.falsify(cls.run_sequence, [cls.produce_step])[0]
