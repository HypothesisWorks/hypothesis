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

    def simplify_such_that(self, t, f):
        tracker = Tracker()

        while True:
            for s in self.simplify(t):
                if tracker.already_seen(s): 
                    continue

                if f(s):
                    t = s
                    break
            else:
                return t  

DEFAULT_SIMPLIFIERS = Simplifiers()

def simplifies(typ):
    def accept_function(fn):
        DEFAULT_SIMPLIFIERS.define_simplifier_for(typ, fn)
        return fn
    return accept_function

def _convert_key(x):
    if isinstance(x, list):
        return tuple(map(_convert_key,x))
    if isinstance(x, tuple):
        return tuple(map(_convert_key,x))
    if isinstance(x, dict):
        return tuple(sorted(map(_convert_key,x.items())))
    if isinstance(x, set):
        return frozenset(map(_convert_key, x))
    return x

class Tracker():
    def __init__(self):
        self.contents = {}

    def already_seen(self,x):
        ck = x.__class__
        x = _convert_key(x)
        try:
            seen_set = self.contents[ck]
            present = x in seen_set
            if not present:
                if isinstance(seen_set, set):
                    seen_set.add(x)
                else: 
                    seen_set.append(x)
            return present
        except KeyError:
            try:
                seen_set = set(x)
            except TypeError:
                seen_set = [x] 

            self.contents[ck] = seen_set
            return False
        return seen_set

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
def simplify_integer(simplifiers, x):
    if x < 0:
        yield -x
        for y in xrange(x+1, 1): yield y
    elif x > 0:
        for y in xrange(x-1,-1,-1): yield y

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
            for i in xrange(n,49):
                yield chr(i)
        elif n > 48:
            for i in xrange(n,47,-1):
                yield chr(i)
    else:
        for y in simplifiers.simplify(list(x)):
            yield ''.join(y)

@simplifies(tuple)
def simplify_tuple(simplifiers, x):
    """
    Defined simplification for tuples: We don't change the length of the tuple
    we only try to simplify individual elements of it.
    We first try simplifying each index. We then try pairs of indices.
    After that we stop because it's getting silly. 
    """
    for i in xrange(0, len(x)):
        for s in simplifiers.simplify(x[i]):
            z = list(x)
            z[i] = s
            yield tuple(z)
    for i in xrange(0, len(x)):
        for j in xrange(0, len(x)):
            if i == j: continue
            for s in simplifiers.simplify(x[i]):
                for t in simplifiers.simplify(x[j]):
                    z = list(x)
                    z[i] = s
                    z[j] = t
                    yield tuple(z)

@simplifies(dict)
def simplify_dict(simplifiers, x):
    for k in x:
        y = dict(x)
        del y[k]
        yield y
    for k in x:
        for v in simplifiers.simplify(x[k]):
            y = dict(x)
            y[k] = v
            yield y


