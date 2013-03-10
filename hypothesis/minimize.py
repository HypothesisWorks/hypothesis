__minimizers__ = {}

def minimizes(typ):
    def accept_function(fn):
        define_minimizer_for(typ, fn)
        return fn
    return accept_function

def __minimizer_key(t):
    return t.__class__

def minimizer_for(t):
    try:
        return __minimizers__[__minimizer_key(t)]
    except KeyError:
        return nothing_to_minimize

def minimizer(t):
    return minimizer_for(t)(t)

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

def minimize_such_that(t, f):
    tracker = Tracker()

    while True:
        for s in minimizer(t):
            if tracker.seen(s): 
                continue
            else:
                tracker.add(s)
            if f(s):
                t = s
                break
        else:
            return t  

def define_minimizer_for(t, m):
    __minimizers__[t] = m

def nothing_to_minimize(x):
    return []

@minimizes(float)
def minimize_float(x):
    yield 0.0
    if x < 0: yield -x
    n = int(x)
    yield float(n)
    for m in minimizer(n):
        yield float(m)    
        yield (m - n) + x

@minimizes(int)
def minimize_integer(x):
    if x < 0:
        yield -x
        for y in xrange(x+1, 1): yield y
    elif x > 0:
        for y in xrange(x-1,-1,-1): yield y

@minimizes(list)
def minimize_list(x):
    indices = xrange(0, len(x)) 
    for i in indices:
        y = list(x)
        del y[i]
        yield y

    for i in indices:
        for s in minimizer(x[i]):
            z = list(x)
            z[i] = s
            yield z 

@minimizes(str)
def minimize_string(x):
    if len(x) == 0:
        return
    elif len(x) == 1:
        yield ''
        for i in minimizer(ord(x)):
            yield chr(i)
    else:
        for y in minimizer(list(x)):
            yield ''.join(y)

@minimizes(tuple)
def minimize_tuple(x):
    for i in xrange(0, len(x)):
        for s in minimizer(x[i]):
            z = list(x)
            z[i] = s
            yield tuple(z)

@minimizes(dict)
def minimize_dict(x):
    for k in x:
        y = dict(x)
        del y[k]
        yield y
    for k in x:
        for v in minimizer(x[k]):
            y = dict(x)
            y[k] = v
            yield y


