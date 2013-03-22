from hypothesis.specmapper import SpecificationMapper
from random import random, choice,sample
import math
from math import log, log1p
from inspect import isclass
from itertools import islice
from types import FunctionType, MethodType
from contextlib import contextmanager

def log2(x): return log(x) / log(2)

def produces(typ):
    def accept_function(fn):
        Producers.default().define_specification_for(typ, lambda _: fn)
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

    def producer(self, descriptor):
        return self.specification_for(descriptor)

    def missing_specification(self, descriptor):
        if isinstance(descriptor, FunctionType) or isinstance(descriptor, MethodType):
            return descriptor
        return SpecificationMapper.missing_specification(self, descriptor)

    def produce(self,typs, size):
        return self.producer(typs)(self,size)

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


@produces(float)
def random_float(self,size):
    may_be_negative = size > 1
    if may_be_negative:
        size -= 1
    mean = math.exp(size - 1)
    x = -log(random()) * mean
    if may_be_negative and flip_coin():
        x = -x
    return x


@produces(bool)
def flip_coin(*args):
    return random() <= 0.5
