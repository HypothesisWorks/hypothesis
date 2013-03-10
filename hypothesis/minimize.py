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

def minimize_such_that(t, f):
    if not f(t):
        raise ValueError("Value %s does not satisfy predicate %s" % (t, f))

    while True:
        for s in minimizer(t):
            if f(s):
                t = s
                break
        else:
            return t  

def define_minimizer_for(t, m):
    __minimizers__[t] = m

def nothing_to_minimize(x):
    return []

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

