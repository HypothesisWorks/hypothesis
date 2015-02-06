from hypothesis.descriptortests import descriptor_test_suite
from hypothesis.descriptors import one_of, integers_in_range
from random import Random
from hypothesis.internal.compat import binary_type, text_type


TestOneOf = descriptor_test_suite(one_of((int, bool)))
TestOneOfSameType = descriptor_test_suite(
    one_of((integers_in_range(1, 10), integers_in_range(8, 15)))
)
TestRandom = descriptor_test_suite(Random)
TestInts = descriptor_test_suite(int)
TestBoolLists = descriptor_test_suite(
    [bool], simplify_is_unique=False
)
TestString = descriptor_test_suite(
    text_type, simplify_is_unique=False
)
BinaryString = descriptor_test_suite(
    binary_type, simplify_is_unique=False
)
TestIntBool = descriptor_test_suite((int, bool))
TestFloat = descriptor_test_suite(float)
TestComplex = descriptor_test_suite(complex)
TestComplex = descriptor_test_suite((float, float))
