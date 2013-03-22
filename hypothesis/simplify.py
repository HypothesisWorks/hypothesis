from hypothesis.tracker import Tracker

class Simplifiers:
    def __init__(self):
        self.__simplifiers = {} 

    def __simplifier_key(self,t):
        return t.__class__

    def simplify(self, t):
        return self.simplifier_for(t)(self, t)

    def simplifier_for(self,t):
        try:
            return self.__simplifiers[self.__simplifier_key(t)]
        except KeyError:
            if self is DEFAULT_SIMPLIFIERS:
                return no_simplifications
            else:
                return DEFAULT_SIMPLIFIERS.simplifier_for(t)

    def define_simplifier_for(self, t, m):
        self.__simplifiers[t] = m


DEFAULT_SIMPLIFIERS = Simplifiers()

def simplifies(typ):
    def accept_function(fn):
        DEFAULT_SIMPLIFIERS.define_simplifier_for(typ, fn)
        return fn
    return accept_function
def no_simplifications(s,x):
    return []

@simplifies(float)
def simplify_float(simplifiers, x):
    yield 0.0
    if x < 0: yield -x
    n = int(x)
    yield float(n)
    for m in simplifiers.simplify(n):
        yield float(m)    
        yield (m - n) + x

@simplifies(int)

@simplifies(list)
def simplify_list(simplifiers, x):
    indices = xrange(0, len(x)) 
    for i in indices:
        y = list(x)
        del y[i]
        yield y

    for i in indices:
        for s in simplifiers.simplify(x[i]):
            z = list(x)
            z[i] = s
            yield z 

    for i in xrange(0,len(x) - 1):
        for j in xrange(i,len(x) - 1):
            y = list(x)
            del y[i]
            del y[j]
            yield y
           

@simplifies(set)
def simplify_set(simplifiers, x):
    for y in simplifiers.simplify(list(x)):
        yield set(y)

@simplifies(str)
def simplify_string(simplifiers,x):
    if len(x) == 0:
        return
    elif len(x) == 1:
        yield ''
        n = ord(x)
        if n < 48:
            yield chr(48 * 2 - n)
            for i in xrange(n,49):
                yield chr(i)
        elif n > 48:
            for i in xrange(n,47,-1):
                yield chr(i)
    else:
        for y in simplifiers.simplify(list(x)):
            yield ''.join(y)


    # Interesting things can happen with duplicate values. We now look for any
    # values which appear in the tuple more than twice (we covered ones which 
    # appear only twice before) and try to simplify them in lockstep.
    t = Tracker()
    for v in x:
        t.track(v)

    for v, n in t:
        if n > 2:
            for s in simplifiers.simplify(v):
                yield tuple((s if y == v else y for y in x))
            

