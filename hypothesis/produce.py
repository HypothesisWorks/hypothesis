from random import random, choice,sample
from math import log
from inspect import isclass
from itertools import islice

__producers__ = {}

DEFAULT_producer_SIZE=10

def produces(typ):
    def accept_function(fn):
        define_producer_for(typ, fn)
        return fn
    return accept_function

def producer(typ):
    if not typ:
        raise ValueError("producer requires at least one type argument")

    if isclass(typ):
        return __producers__[typ]
    elif isinstance(typ,tuple):
        return tuple_producer(map(producer, typ))
    elif isinstance(typ, list):
        if not typ:
            raise ValueError("Array arguments must be non-empty")
    
        gen = one_of(*map(producer,typ)) 
        return list_producer(gen)   
    elif isinstance(typ,dict):
        return dict_producer(typ)
    else:
        raise ValueError("I don't understand the argument %typ")

def produce(typs, size=DEFAULT_producer_SIZE,):
    if size <= 0 or not isinstance(size,int):
        raise ValueError("Size  %s should be a positive integer" % size)

    return producer(typs)(size)

def define_producer_for(t, m):
    __producers__[t] = m

def tuple_producer(tup):
    return lambda size: tuple([g(size) for g in tup])

def list_producer(elements):
    return lambda size: [elements(size) for _ in xrange(produce(int, size))]

def dict_producer(producer_dict):
    def gen(size):
        result = {}
        for k,g in producer_dict.items():
            result[k] = g(size)
        return result
    return gen

def one_of(*args):
    """
    Takes n producers as arguments, returns a producer which calls each
    with equal probability
    """
    if len(args) == 1:
        return args[0]
    return lambda size: choice(args)(size)

def random_float(size):
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

def geometric_int(size):
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
def produce_string(size):
    return ''.join((choice(characters) for _ in xrange(produce(int,size))))

def flip_coin():
    return random() <= 0.5

define_producer_for(int, geometric_int)
define_producer_for(float, random_float)
