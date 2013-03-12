__simplifiers__ = {}

def simplifies(typ):
    def accept_function(fn):
        define_simplifier_for(typ, fn)
        return fn
    return accept_function

def __simplifier_key(t):
    return t.__class__

def simplifier_for(t):
    try:
        return __simplifiers__[__simplifier_key(t)]
    except KeyError:
        return no_simplifications

def simplifier(t):
    return simplifier_for(t)(t)

def _convert_key(x):
    if isinstance(x, list):
        return tuple(map(_convert_key,x))
    if isinstance(x, tuple):
        return tuple(map(_convert_key,x))
    if isinstance(x, dict):
        return tuple(sorted(map(_convert_key,x.items())))
    return x

class Tracker():
    def __init__(self):
        self.contents = {}

    def seen_set(self,x):
        ck = x.__class__
        try:
            seen_set = self.contents[ck]
        except KeyError:
            seen_set = set()
            self.contents[ck] = seen_set
        return seen_set

    def add(self,x):
        self.seen_set(x).add(_convert_key(x))
    
    def seen(self,x):
        return _convert_key(x) in self.seen_set(x)

def simplify_such_that(t, f):
    tracker = Tracker()

    while True:
        for s in simplifier(t):
            if tracker.seen(s): 
                continue
            else:
                tracker.add(s)
            if f(s):
                t = s
                break
        else:
            return t  

def define_simplifier_for(t, m):
    __simplifiers__[t] = m

def no_simplifications(x):
    return []

@simplifies(float)
def simplify_float(x):
    yield 0.0
    if x < 0: yield -x
    n = int(x)
    yield float(n)
    for m in simplifier(n):
        yield float(m)    
        yield (m - n) + x

@simplifies(int)
def simplify_integer(x):
    if x < 0:
        yield -x
        for y in xrange(x+1, 1): yield y
    elif x > 0:
        for y in xrange(x-1,-1,-1): yield y

@simplifies(list)
def simplify_list(x):
    indices = xrange(0, len(x)) 
    for i in indices:
        y = list(x)
        del y[i]
        yield y

    for i in indices:
        for s in simplifier(x[i]):
            z = list(x)
            z[i] = s
            yield z 

@simplifies(str)
def simplify_string(x):
    if len(x) == 0:
        return
    elif len(x) == 1:
        yield ''
        n = ord(x)
        if n < 48:
            for i in xrange(n,49):
                yield chr(i)
        elif n > 48:
            for i in xrange(n,47,-1):
                yield chr(i)
    else:
        for y in simplifier(list(x)):
            yield ''.join(y)

@simplifies(tuple)
def simplify_tuple(x):
    for i in xrange(0, len(x)):
        for s in simplifier(x[i]):
            z = list(x)
            z[i] = s
            yield tuple(z)

@simplifies(dict)
def simplify_dict(x):
    for k in x:
        y = dict(x)
        del y[k]
        yield y
    for k in x:
        for v in simplifier(x[k]):
            y = dict(x)
            y[k] = v
            yield y


