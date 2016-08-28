---
layout: post
tags: technical python intro
date: 2016-08-28 15:00
title: Hypothesis vs. Eris
published: true
author: drmaciver
---

[Eris](https://github.com/giorgiosironi/eris/) is a library for property-based testing of PHP code, inspired by the mature frameworks that other languages provide like [QuickCheck](https://hackage.haskell.org/package/QuickCheck), Clojure's [test.check](https://github.com/clojure/test.check) and of course Hypothesis.

Here is a side-by-side comparison of some basic and advanced features that have been implemented in both Hypothesis and Eris, which may help developers coming from either Python or PHP and looking at the other side.

<!--more-->

## Hello, world

The first example can be considered an `Hello, world` of randomized testing: given two random numbers, their sum should be constant no matter the order in which they are summed. The test case has two input parameters, so that it can be run dozens or hundreds of times, each run with different and increasingly complex input values.

Hypothesis provides an idiomatic Python solution, the `@given` decorator, that can be used to compose the strategies objects instantiated from `hypothesis.strategies`. The test case is very similar to an example-based one, except for the addition of arguments:

```python
import unittest
from hypothesis import given
from hypothesis import strategies as st

class TestEris(unittest.TestCase):
    "Comparing the syntax and implementation of features with Eris"

    @given(st.integers(), st.integers())
    def test_sum_is_commutative(self, first, second):
        x = first + second
        y = second + first
        self.assertEqual(x, y, "Sum between %d and %d should be commutative" % (first, second))
```

Eris provides functionality with a trait instead, that can be composed into the test cases that need access to randomized input. The test method is not augmented with additional parameters, but its code is moved inside an anonymous function for the `then()` primitive. Input distributions are defined in a mathematically-named `forAll()` primitive:

```php
<?php
use Eris\Generator;
use Eris\TestTrait;

class IntegerTest extends PHPUnit_Framework_TestCase
{
    use TestTrait;

    public function testSumIsCommutative()
    {
        $this
            ->forAll(
                Generator\int(),
                Generator\int()
            )
            ->then(function ($first, $second) {
                $x = $first + $second;
                $y = $second + $first;
                $this->assertEquals(
                    $x,
                    $y,
                    "Sum between {$first} and {$second} should be commutative"
                );
            });
    }
```

Both these tests will be run hundreds of times, each computing two sums and comparing them for equality with the assertion library of the underlying testing framework (unittest and PHPUnit).

## Composing strategies

A very simple composition problem consists of generating a collection data structured whose elements are drawn from a known distribution, for example a list of integers. Hypothesis provides *strategies* that can compose other strategies, in this case to build a list of random integers of arbitrary length:

```python
    @given(st.lists(st.integers()))
    def test_reversing_twice_gives_same_list(self, xs):
        ys = list(xs)
        ys.reverse()
        ys.reverse()
        self.assertEqual(xs, ys)
```

Eris calls *generators* the objects representing statistical distributions, but uses the same compositional pattern for higher-order values like lists and all collections:

```php
    public function testArrayReverseIsTheInverseOfItself()
    {
        $this
            ->forAll(
                Generator\seq(Generator\nat())
            )
            ->then(function ($array) {
                $this->assertEquals($array, array_reverse(array_reverse($array)));
            });
    }
```

In both these test cases, we generate a random list and check that reversing it twice brings us back to the original input.

## Filtering generated values

Not all problems are abstract enough to accept all values in input, so it may be necessary to exclude part of the generated values when they do not fit our needs.

Hypothesis provides a `filter()` method to apply a lambda to values, expressing a condition for them to be included in the test:

```python
    @given(st.integers().filter(lambda x: x > 42))
    def test_filtering(self, x):
        self.assertGreater(x, 42)
```

Eris allows to filter values with a predicate in the same way, but prefers to allocate the filter to the generic `ForAll` object rather than decorate it on each Generator:

```php
    public function testWhenWithAnAnonymousFunctionWithGherkinSyntax()
    {
        $this
            ->forAll(
                Generator\choose(0, 1000)
            )
            ->when(function ($n) {
                return $n > 42;
            })
            ->then(function ($number) {
                $this->assertTrue(
                    $number > 42,
                    "\$number was filtered to be more than 42, but it's $number"
                );
            });
    }
```

## Transforming generated values

Another common need consists of transforming the generated value to a different space, for example the set of all even numbers rather than the (larger) set of integers. Hypothesis allows to do this by passing a lambda to the `map()` method of a strategy:

```python
    @given(st.integers().map(lambda x: x * 2))
    def test_mapping(self, x):
        self.assertEqual(x % 2, 0)
```

Eris instead provides a `Map` higher-order generator, which applies the lambda during generation:

```php
    public function testApplyingAFunctionToGeneratedValues()
    {
        $this
            ->forAll(
                Generator\map(
                    function ($n) { return $n * 2; },
                    Generator\nat()
                )
            )
            ->then(function ($number) {
                $this->assertTrue(
                    $number % 2 == 0,
                    "$number is not even"
                );
            });
    }
```

In both cases, the advantage of using the `map` support from the library (rather than writing our own multiplying code in the tests) is that the resulting object can be further composed to build larger data structures like a list or set of even numbers.

## Generators with random parameters

It's possible to build even stricter values, that have internal constraints that must be satisfied but can't easily be generated by applying a pure function to a previously generated value.

Hypothesis provides the `flatmap()` method to pass the output of an inner strategy to a lambda that creates an outer strategy to use in the test. Here a list of 4 integers is passed to the lambda, to generate a tuple consisting of the list and a random element chosen from it:

```python
    @given(st.lists(st.integers(), min_size=4, max_size=4).flatmap(
        lambda xs: st.tuples(st.just(xs), st.sampled_from(xs))
    ))
    def test_list_and_element_from_it(self, pair):
        (generated_list, element) = pair
        self.assertIn(element, generated_list)
```

Eris does the same with a slighly different naming, calling this primitive `bind`:

```php
    public function testCreatingABrandNewGeneratorFromAGeneratedValue()
    {
        $this
            ->forAll(
                Generator\bind(
                    Generator\vector(4, Generator\nat()),
                    function ($vector) {
                        return Generator\tuple(
                            Generator\elements($vector),
                            Generator\constant($vector)
                        );
                    }
                )
            )
            ->then(function ($tuple) {
                list($element, $vector) = $tuple;
                $this->assertContains($element, $vector);
            });
    }
```

## What the future brings

Hypothesis is a much more mature project than Eris, especially when it comes to keeping state between test runs or acting as a generic random data provider rather than as an extension to a testing framework. It will be interesting to continue porting Hypothesis features to the PHP world, given the original features and patterns that Hypothesis shows with respect to the rest of the `*Check` world. 

## References

The Hypothesis examples shown in this post can be found in [this example repository](https://github.com/giorgiosironi/hypothesis-exploration/blob/master/test_eris.py).

The Eris examples can instead be found in the example/ folder of [the](https://github.com/giorgiosironi/eris/blob/master/examples/IntegerTest.php#L9) [Eris](https://github.com/giorgiosironi/eris/blob/master/examples/SequenceTest.php#L9) [repository](https://github.com/giorgiosironi/eris/blob/master/examples/WhenTest.php#L8) [on](https://github.com/giorgiosironi/eris/blob/master/examples/MapTest.php#L8) [Github](https://github.com/giorgiosironi/eris/blob/master/examples/BindTest.php#L8).
