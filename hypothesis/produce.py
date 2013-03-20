from random import random, choice,sample
import math
from math import log, log1p
from inspect import isclass
from itertools import islice
from types import FunctionType, MethodType
from contextlib import contextmanager


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
        DEFAULT_PRODUCERS.define_producer_for(typ, fn)
        return fn
    return accept_function

def produces_from_instances(typ):
    def accept_function(fn):
        DEFAULT_PRODUCERS.define_producer_for_instances(typ, fn)
        return fn
    return accept_function

class Producers:
    def __init__(self):
        self.__producers = {}
        self.__instance_producers = {}
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

    def producer(self, typ):
        if isinstance(typ, FunctionType) or isinstance(typ, MethodType):
            return typ

        try:
            if isclass(typ):
                return self.__producers[typ]
            else:
                return self.__instance_producers[typ.__class__](typ)
        except KeyError as e:
            if self is DEFAULT_PRODUCERS:
                if isclass(typ):
                    raise ValueError("No producer defined for type %s" % str(typ))
                else:
                    raise ValueError("No instance producers defined for %s" % str(typ))
            else:
                return DEFAULT_PRODUCERS.producer(typ)

    def produce(self,typs, size):
        with reset_on_exit(self):
            if size <= 0 or not isinstance(size,int):
                raise ValueError("Size  %s should be a positive integer" % size)

            return self.producer(typs)(self,size)

    def define_producer_for(self,t, m):
        self.__producers[t] = m

    def define_producer_for_instances(self,t, m):
        self.__instance_producers[t] = m

DEFAULT_PRODUCERS = Producers()

@produces_from_instances(tuple)
def tuple_producer(tup):
    return lambda self,size: tuple([self.producer(g)(self,size) for g in tup])

@produces_from_instances(list)
def list_producer(elements):
    element_producer = one_of(*elements)
    return lambda self,size: [element_producer(self,size) for _ in xrange(self.produce(int, size))]

@produces_from_instances(set)
def set_producer(elements):
    return map_producer(set, list_producer(elements))
    
def map_producer(f, producer):
    return lambda ps,size: f(producer(ps, size))

@produces_from_instances(dict)
def dict_producer(producer_dict):
    def gen(self,size):
        result = {}
        for k,g in producer_dict.items():
            print k, self, size
            result[k] = self.producer(g)(self,size)
        return result
    return gen

def one_of(*args):
    """
    Takes n producers as arguments, returns a producer which calls each
    with equal probability
    """
    return lambda self,size: self.producer(choice(args))(self,size)

@produces(float)
def random_float(self,size):
    allow_negatives = self.is_flag_enabled("allow_negative_numbers", size)

    if random() <= 0.05:
        if allow_negatives and flip_coin():
            return -0.0
        else:
            return 0.0
    else:
        x = -log(random()) * size
        if flip_coin():
            x = 1/x
        if allow_negatives and flip_coin():
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
