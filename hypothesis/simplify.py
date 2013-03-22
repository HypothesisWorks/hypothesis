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


@simplifies(set)
def simplify_set(simplifiers, x):
    for y in simplifiers.simplify(list(x)):
        yield set(y)
