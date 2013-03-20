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

def requires(*args):
    def alter_function(f):
        f.hypothesis_test_requirements = args
        return f
    return alter_function


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
        step = choice(cls.test_steps())
        try:
            requirements = step.hypothesis_test_requirements
        except AttributeError:
            requirements = ()
        return (step,producers.produce(requirements, size))

    @classmethod
    def run_sequence(cls, steps):
        tests = cls.integrity_tests()
        value = cls()
        def run_integrity_tests():
            for t in tests:
                t(value)
        run_integrity_tests()
        for step, args in steps:
            try:
                step(value, *args)
                run_integrity_tests()
            except PreconditionNotMet:
                pass
        return True

    @classmethod
    def breaking_example(cls):
       return hypothesis.falsify(cls.run_sequence, [cls.produce_step])[0]
