from random import random, choice,sample
from math import log
from inspect import isclass
from itertools import islice
from types import FunctionType, MethodType

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

    def producer(self, typ):
        if not typ:
            raise ValueError("producer requires at least one type argument")
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
    if random() <= 0.05:
        if flip_coin():
            return -0.0
        else:
            return 0.0
    else:
        x = -log(random()) * size
        if flip_coin():
            x = 1/x
        if flip_coin():
            x = -x
    return x

@produces(int)
def geometric_int(self,size):
    """
    produce a geometric integer with expected absolute value size and sign
    negative or positive with equal probability
    """
    p = 1.0 / (size + 1)
    n =  int(log(random()) / log(1 - p))
    if random() <= 0.5:
        n = -n
    return n

characters = map(chr,range(0,127))

@produces(str)
def produce_string(self,size):
    return ''.join((choice(characters) for _ in xrange(self.produce(int,size))))

@produces(bool)
def flip_coin():
    return random() <= 0.5
