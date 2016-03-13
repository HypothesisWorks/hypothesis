from typing import List, NamedTuple, Optional, Tuple, Union
import unittest 
from hypothesis.extra.typehints import type_to_strat, func_strat
from hypothesis import given, assume
from hypothesis.strategies import just, random_module
import operator
try:
    from functools import reduce
except:
    pass
fields = [('ref', str),
          ('AO', List[int]),
          ('DP', int),
          ('chrom',str),
          ('pos', int),
          ('alt', List[str])]
 
VCFRow = NamedTuple("VCFRow", fields)
class TypeHintsTests(unittest.TestCase):
    @given(type_to_strat(VCFRow))
    def test_namedtuple_vcfrow(self, obj):
        for attr, typ in fields:
            self.assertIsInstance(getattr(obj, attr), typ)
    
    def test_func_strat(self): 
       #def example_func(m: int, xs: List[int]) -> None:
      def example_func(m, xs):
         # type: (int, List[int]) -> None
         self.assertIsInstance(xs, List[int])
         self.assertIsInstance(m, int)
      argtypes = {'m' : int, 'xs' : List[int], 'return' : None}
      example_func.__annotations__ = argtypes
      strat = func_strat(example_func)
      for _ in range(20):
          example_func(**strat.example()) 
    
    SimpleObj = NamedTuple("SimpleObj", [('int', int), ('bool', bool)])
    some_types = [int, str, Optional[int], List[Tuple[int,str]], Tuple[bool, int], SimpleObj]
    atype = reduce(operator.ior, map(just, some_types))
    
    
    @given(atype, atype, atype, random_module())
    def test_union_is_either(self, t1, t2, t3, _):
        union = Union[t1, t2, t3]
        strat = type_to_strat(union)
        for _ in range(20):
            ex = strat.example()
            self.assertIsInstance(ex, (t1, t2, t3))
    
    @given(type_to_strat(Union[int, str]))
    def test_union_produces_first(self, x):
        assume(isinstance(x, int))
        self.assertIsInstance(x, int)
    
    @given(type_to_strat(Union[int, str]))
    def test_union_produces_second(self, y):
        assume(isinstance(y, str))
        self.assertIsInstance(y, str) 
