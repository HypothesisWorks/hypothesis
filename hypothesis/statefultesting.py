from functools import wraps
from random import choice
from hypothesis.verifier import Verifier
from hypothesis.simplify import simplifies
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


class TestRun:
    def __init__(self,cls, steps):
        self.cls = cls
        self.steps = steps

    def run(self):
        tests = self.cls.integrity_tests()
        value = self.cls()
        def run_integrity_tests():
            for t in tests:
                t(value)
        run_integrity_tests()
        for step, args in self.steps:
            try:
                step(value, *args)
                run_integrity_tests()
            except PreconditionNotMet:
                pass
        return True

    def prune(self):
        results = []
    
        v = self.cls()
        for s in self.steps:
            try:
                s[0](v, *s[1])
                results.append(s)
            except PreconditionNotMet:
                continue
            except:
                results.append(s)
                break
        if len(results) == len(self): 
            return None
        else: 
            return TestRun(self.cls,results)
                
    def __eq__(self,that):
        return self.cls == that.cls and self.steps == that.steps

    def __hash__(self):
        # Were we want to hash this we want to rely on Tracker's logic for
        # hashing collections anyway
        raise TypeError("unhashable type 'testrun'")

    def __len__(self):
        return len(self.steps)

    def __iter__(self):
        return self.steps.__iter__()

    def __getitem__(self, i):
        return self.steps[i]

@simplifies(TestRun)
def simplify_test_run(simplifiers, test_run):
    pruned = test_run.prune()
    if pruned:
        yield pruned
    for x in simplifiers.simplify(test_run.steps):
        yield TestRun(test_run.cls, x)
    methods =  tuple((s[0] for s in test_run))
    arguments = tuple((s[1] for s in test_run))
    for sargs in simplifiers.simplify(arguments):
        yield  TestRun(test_run.cls, zip(methods, sargs))



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
    def produce_testrun(cls,producers,size):
        return TestRun(cls, producers.produce([cls.produce_step], size)) 

    @classmethod
    def breaking_example(cls):
        test_run = hypothesis.falsify(TestRun.run, cls.produce_testrun)[0]
        return [(f.__name__,) + args for f, args in test_run]
