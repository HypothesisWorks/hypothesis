def is_atom(k):
    t = type(k)
    return (t == int or 
            t == str or 
            t == bool or 
            t == float or
            t == complex
           )

def use_native_equality(k):
    return is_atom(k) or isinstance(k, set) or isinstance(k, frozenset)

def recursive_eq(x, y, state=None):
    if x is y: return True
    if type(x) != type(y): return False
    if use_native_equality(x): return x == y

    try:
        if len(x) != len(y):
            return False
    except TypeError:
        pass

    if isinstance(x, dict):
        for k, v in x.items():
            try:
                v2 = y[k]
            except KeyError:
                return False
            if not recursive_eq(v, v2):
                return False
        return True 

    state = state or []

    if any(( a is x and b is y for a, b in state)): 
        return True
    
    try:
        starting_length = len(state)
        state.append((x,y))
        try:
            xs = iter(x)
            ys = iter(y)
        except TypeError:
            return recursive_eq(x.__dict__, y.__dict__, state)
    
        for a,b in zip(xs, ys):
            if not recursive_eq(a,b,state): return False
        return True
    finally:
        state.pop()
        assert len(state) == starting_length

def recursive_hash(x, state=None):
    return 0    

class DescriptorKey(object):
    """
    Wraps possibly recursive objects and does structural equality tests on them
    Also hashes correctly.
    """

    def __init__(self, key):
        self.key = key
        self.h = recursive_hash(key)

    def __eq__(self, other):
        if not isinstance(other, DescriptorKey): return False
        else: return recursive_eq(self.key, other.key)

    def __ne__(self, other):
        return not(self == other)
