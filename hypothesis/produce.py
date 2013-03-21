from hypothesis.specmapper import SpecificationMapper
from random import random, choice,sample
import math
from math import log, log1p
from inspect import isclass
from itertools import islice
from types import FunctionType, MethodType
from contextlib import contextmanager

def log2(x): return log(x) / log(2)

@contextmanager
def reset_on_exit(x):
    x.current_depth += 1
    try:
        yield
    finally:
        x.current_depth -= 1
        if not x.current_depth:
            x.reset_state()


def produces(typ):
    def accept_function(fn):
        Producers.default().define_specification_for(typ, fn)
        return fn
    return accept_function

def produces_from_instances(typ):
    def accept_function(fn):
        Producers.default().define_specification_for_instances(typ, fn)
        return fn
    return accept_function

class Producers(SpecificationMapper):
    def __init__(self):
        SpecificationMapper.__init__(self)
        self.current_depth = 0
        self.enabled_flags = {}

    def reset_state(self):
        self.enabled_flags = {}

    def flag_probability(self, size):
        x = size / 50.0
        return x / (1 + x) 

    def is_flag_enabled(self, flag, size):
        if flag in self.enabled_flags:
            return self.enabled_flags[flag]

        result = random() <= self.flag_probability(size) 
        self.enabled_flags[flag] = result
        return result

    def producer(self, descriptor):
        return self.specification_for(descriptor)

    def missing_specification(self, descriptor):
        if isinstance(descriptor, FunctionType) or isinstance(descriptor, MethodType):
            return descriptor
        return SpecificationMapper.missing_specification(self, descriptor)

    def produce(self,typs, size):
        with reset_on_exit(self):
            return self.producer(typs)(self,size)

@produces_from_instances(tuple)
def tuple_producer(producers, tup):
    return lambda self,size: tuple([self.produce(g,size/len(tup)) for g in tup])

@produces_from_instances(list)
def list_producer(producers, elements):
    element_producer = one_of(*elements)

    def produce_list(producers, size):
        # We allocate a larger fraction of the entropy to elements because it's
        # going to spread out more. Also because shorter lists are easier to work
        # with.
        entropy_for_length = 0.25 * size
        length = producers.produce(int, entropy_for_length)
        if length == 0:
            return []
        entropy_for_elements = (size - entropy_for_length) / length
        
        return [producers.produce(element_producer,entropy_for_elements) for _ in xrange(length)]
    return produce_list

@produces_from_instances(set)
def set_producer(producers, elements):
    return map_producer(set, list_producer(producers, elements))
    
def map_producer(f, producer):
    return lambda ps,size: f(producer(ps, size))

@produces_from_instances(dict)
def dict_producer(producers, producer_dict):
    def gen(self,size):
        result = {}
        for k,g in producer_dict.items():
            result[k] = self.producer(g)(self,size)
        return result
    return gen

def one_of(*choices):
    """
    Takes n producers as arguments, returns a producer which calls each
    with equal probability when there is enough entropy to do so and then
    starts taking initial segments in situations of reduced entropy.

    Note that the entropy calculations assume that the choices are disjoint.
    If they are not this will still work fine, but the entropy values will be
    a bit off.
    """
    if len(choices) == 1:
        return choices[0]

    def produce_one_of(producers, size):
        if size <= log2(len(choices)):
            n = int(2 ** size)
            restricted_choices = choices[0:n]
        else:
            restricted_choices = choices
        size -= log2(len(restricted_choices))
        return producers.produce(choice(restricted_choices), size)
            
    return produce_one_of

@produces(float)
def random_float(self,size):
    may_be_negative = size > 1 and self.is_flag_enabled("allow_negative_numbers", size)
    if may_be_negative:
        size -= 1
    mean = math.exp(size - 1)
    x = -log(random()) * mean
    if may_be_negative and flip_coin():
        x = -x
    return x

def geometric_probability_for_entropy(desired_entropy):
    def h(p):
        if p <= 0:
            return float('inf')
        if p >= 1:
            return 0
        try:
            q = 1 - p
            return -(q * log(q) + p * log(p))/(log(2) * p)
        except ValueError:
            return 0.0
    lower = 0.0
    upper = 1.0
    for _ in xrange(max(int(desired_entropy * 2), 1024)):
        mid = (lower + upper) / 2
        if h(mid) > desired_entropy:
            lower = mid
        else:
            upper = mid
    return mid

@produces(int)
def produce_int(self,size):
    can_be_negative = size > 1 and self.is_flag_enabled("allow_negative_numbers", size)
  
    if size <= 0:
        return 0
 
    if can_be_negative:
        size -= 1
    p = 1.0 / (size + 1)
    n =  int(log(random()) / log1p(- p))
    if can_be_negative and random() <= 0.5:
        n = -n
    return n

characters = map(chr,range(0,127))

@produces(str)
def produce_string(self,size):
    return ''.join((choice(characters) for _ in xrange(self.produce(int,size))))

@produces(bool)
def flip_coin(*args):
    return random() <= 0.5
