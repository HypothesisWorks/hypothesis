from __future__ import print_function
import sys
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy
from typing import Dict, Tuple, List, Iterator, Set, Union, Optional, NamedTuple, Callable, Sequence, Iterable, Generator
import operator
from collections import OrderedDict
compose = lambda f,g: lambda *x: f(g(*x))
# see https://docs.python.org/3/library/typing.html
try:
    unicode = unicode
except:
    unicode = str
    from functools import reduce

primitives = {
    str   : st.text(), # might want to default to `string.printable`
    int   : st.integers(),
    bool  : st.booleans(),
    float : st.floats(),
    type(None) : st.none(),
    unicode : st.characters(),
    bytes : st.binary() # this is weird because str == bytes in py2
} # missing: fractions, decimal

# it's not possible to make this typesafe, because 
# we need `issinstance` to narrow down the types of types, 
# and we are using `issubclass`
# there's also a FrozenSet type
# IO types ("file-like")
# re type
def type_to_strat(x): # type: (type) -> SearchStrategy
   '''
   Given a type, return a strategy which yields a value of that type. Types maybe complex: Union, NamedTuple, etc.
   For more information, see https://docs.python.org/3/library/typing.html
   Usage:
   >> type_to_strat(Union[int,str]).exmample()
   . . . 3
   '''
   if x in primitives:
       return primitives[x]
   elif hasattr(x, '_fields'):# NamedTuple isn't a type, it's a function
   #elif isinstance(x, Callable): #this catches List[T] for some reason
       name = x.__name__
       fts = OrderedDict(x._field_types)
       vals = map(type_to_strat, fts.values()) 
       # `NamedTuple` is actually a ... `namedtuple` itself
       toArgDict = lambda xs: dict(zip(fts.keys(), xs))
       return st.tuples(*vals).map(lambda ys: x(**toArgDict(ys)))
   elif issubclass(x, Dict):
       return st.dictionaries(*map(type_to_strat, x.__parameters__))
   elif issubclass(x, Tuple): 
       if x.__tuple_use_ellipsis__: # variable lenth tuple
           element_type = x.__tuple_params__[0]
           return type_to_strat(List[element_type]).map(tuple) 
       return st.tuples(*map(type_to_strat, x.__tuple_params__))
   elif issubclass(x, Union):
       return reduce(operator.ior, map(type_to_strat, x.__union_params__))
   elif issubclass(x, Optional):
       # Optional[X] is equivalent to Union[X, type(None)]. second param is always Nonetype.
       value = x.__union_params__[0] 
       return (type_to_strat(value) | st.none()) # type: SearchStrategy
   else:
       element_type = type_to_strat(x.__parameters__[0]) 
       if issubclass(x, list):
           return st.lists(element_type)
       elif issubclass(x, set):
           return st.sets(element_type)
       elif issubclass(x, Sequence):
           anySizeTuple = type_to_strat(Tuple[element_type,...]) 
           return st.sets(element_type) | st.lists(element_type) | anySizeTuple 
       elif issubclass(x, Generator):
           toGen = lambda xs: (x for x in xs) # type: Callable[[Iterable[T]], Generator[T]]
           return type_to_strat(List[element_type]).map(toGen)
       # not sure how to create an Iterable (it doesn't have an `__next__` method)
       elif issubclass(x, Iterator)  or issubclass(x, Iteratable):
           return type_to_strat(List[element_type]).map(iter)
       else:
           raise ValueError("Could not find strategy for type %s" % x) 


def func_strat(f): 
    # type: (Callable[...]) -> Dict[str,SearchStrategy[Any]]
    '''
    Given an annotated function, return a strategy which yields a dictionary mapping from the argument names to the appropriate type.
    Usage:
    >> def mod_list_example(m: int, xs: List[int]) -> List[int]:
    >>    return list(map(lambda x: x % m, xs))
    >> mod_list_example(**func_strat(mod_list_example).example())
    >> mod_list_example(**func_strat(mod_list_example).example())
    '''
    argtypes = OrderedDict(f.__annotations__)
    if 'return' in  argtypes:
        del argtypes['return']
    vals = map(type_to_strat, argtypes.values()) 
    toArgDict = lambda xs: dict(zip(argtypes.keys(), xs))
    return st.tuples(*vals).map(toArgDict)

# see https://docs.python.org/3/library/typing.html
# not Generics
# not Callables
