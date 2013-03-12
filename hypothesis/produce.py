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
    def gen(size):
        producers = [g(size) for g in tup]
        while True:
            yield tuple((g.next() for g in producers))
    return gen

def list_producer(elements):
    def gen(size):
        element_producer = elements(size)
        length_producer = produce(int, size)
        while True:
            length = abs(length_producer.next())
            yield list(islice(element_producer, length))
    return gen

def dict_producer(producer_dict):
    def gen(size):
        producers = [(k,producer(v)(size)) for (k,v) in producer_dict.items()]
        while True:
            result = {}
            for k,g in producers:
                result[k] = g.next()
            yield result
    return gen

def repeatedly_yield(f):
    def gen(size):
        while True:
            yield f(size)
    return gen

def one_of(*args):
    """
    Takes n producers as arguments, returns a producer which calls each
    with equal probability
    """
    if len(args) == 1:
        return args[0]
    def gen(size):
        producers = map(lambda a: a(size), args)
        while True:
            yield choice(producers).next()
    return gen

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
    length_producer = produce(int,size)
    for l in length_producer:
        yield ''.join((choice(characters) for _ in xrange(l)))

def flip_coin():
    return random() <= 0.5

define_producer_for(int, repeatedly_yield(geometric_int))
define_producer_for(float, repeatedly_yield(random_float))
