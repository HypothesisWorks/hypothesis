---
tags: python intro technical properties
date: 2020-06-08 15:00
title: Property Testing with Complex Inputs
author: hwayne
---

Once you learn the basics, there are two hard parts to using property-based testing:

* What are good properties to test?
* How do I generate complex inputs?

These are also the the _main_ parts of property-based testing! And both require some skill and creativity to solve. This post is to help you get some basics on the second question, how we generate complex inputs. Often we're working with data that has lots of preconditions and we want to actually generate inputs that satisfies the preconditions. We also often need to create data that depends on other data, or data with extra conditions, or [independent-but-similar](https://www.hillelwayne.com/post/metamorphic-testing/) data. We need some way to build more complex strategies.

There are a few different ways to do this, so let's go into each of them.

## The problem

We have an Exam which consists of a set of questions and multiple-choice answers. Students take ExamInstances, which consists of the exam they took and the answers they gave. For each question they may either list an answer or leave it blank. There are many things we could test here, but the first step is actually generating the data.

For the purposes of this tutorial we will make the data classes as simple as possible:

```py
import typing as t
from dataclasses import field, dataclass

@dataclass
class Exam:
    """The abstract exam. Students take ExamInstances."""
    name: str
    answer_key: t.List[int]

@dataclass
class ExamInstance:
    """The instantiation of the exam."""
    student: int
    exam: Exam
    answers: t.List[t.Optional[int]] # must be same length, but answers may be blank
```

For our property tests we need to generate both Exams and ExamInstances. We have some restrictions on the Exam, and we need the ExamInstances to match the Exam in terms of answer length. This makes it somewhat more complex than the usual "generate an integer" case.

Note: all examples use [pytest](https://docs.pytest.org/en/latest/).

## Generating Exams

### Type inference

We don't _have to_ write a special generator for Exam. We've already type-annotated every field of Exam, so Hypothesis is smart enough to generate valid Exams via the `from_type` strategy.



```py
from hypothesis import given
import hypothesis.strategies as s

@given(s.from_type(Exam))
def test_1(exam):
    ...
```

In fact, it can even generate valid ExamInstances, as all those fields are typed, too:

```py
@given(s.from_type(ExamInstance))
def test_2(ei):
    ...
```

Sometimes this is good enough. In our case it is not for a couple of reasons:

* The state space is huge. Hypothesis is using the default generators for each of the fields, when for our purposes they should be more constrained. The more narrowly we can constrain the search space the more likely we are to get interesting edge cases.
* Hypothesis is going to generate a lot of "nonsensical" exams. You might get something where the answer key is `[-45, 0, 800002]`. We want to use stricter strategies for the fields of Exam.

### Simple customizations

If our requirements are simple and we know that most generated inputs will be correct, we can usually get away with using `filter` and `assume`. `filter` is a method on all strategies, while `assume` goes in the body of the test itself. Both of them, when false, tell hypothesis to discard the invalid data and make a new draw. We can also use `assume` to relate several parameters to each other.

```py
@given(s.from_type(Exam).filter(lambda x: x.answer_key and min(x.answer_key) >= 0))
def test_2(exam):
    assume(max(exam.answer_key) <= 5)
    ...
```

The upside of `filter` and `assume` is that they're easy to write and clearly express what our constraints are. The downside is that we are still generating bad inputs- we're just throwing it away right after. This makes the testing slower and Hypothesis might not find enough valid inputs.

We're better off writing a customized generator that _always_ generates good inputs. Fortunately that's a lot easier than it sounds.


### `builds`

The `builds` strategy takes in an object and a set of initialization strategies, draws the corresponding values, and passes them into the object's `__init__`. Let's say we want to make sure that `answer_key` only uses numbers between 1 and 5. We can use `builds` to do this.

```py
@given(s.builds(Exam, answer_key=s.lists(s.integers(min_value=1, max_value=5))))
def test_3(exam):
    for x in exam.answer_key:
        assert x in range(6)
```



We haven't specified what `name` is, so Hypothesis will use the default generator for text. If we want to always use the same name, we can use the `just` strategy:

```py
@given(s.builds(Exam, name=s.just(""), answer_key=s.lists(s.integers(min_value=1, max_value=5))))
def test_3(exam):
    # same
```

At this point we should probably pull it into its own function:

```py
def exam_strategy():
    return s.builds(Exam,
        name=s.just(""),
        answer_key=s.lists(s.integers(min_value=1, max_value=5)))

@given(exam_strategy())
def test_3(exam):
    # same

```

### `register_type_strategy`

Now that we have a custom builder, we can tell Hypothesis to always use it when inferring Exams. We do this with `register_type_strategy`.

```py
def exam_strategy():
    ...

s.register_type_strategy(Exam, exam_strategy())
```

This will now be used any time Hypothesis infers that it needs to build an Exam, even if it needs to do so as part of generating something else, like an ExamInstance.

```py
@given(s.from_type(Exam))
def test_4(exam):
    ...
```


That takes care of the Exam. But we still have a problem with the ExamInstance: its `answer` must have the same length as its exam's `answer_key`. But there's no way to guarantee that with our builder. We can't link strategies to each other.

 ```py
 # This will fail
@given(s.from_type(ExamInstance))
def test_5(ei):
    assert len(ei.answers) == len(ei.exam.answer_key)
```

In order to combine multiple strategies we need to use something a little more powerful: `composite`.

## `composite`

Composite strategies are user-written functions "lifted" into full strategies. They can be a little bit unintuitive at first, so let's start with a simple example. This composite strategy returns a list of numbers where the first element of the list is always the smallest number in the list:

```py
@s.composite
def example(draw):
    i = draw(s.integers())
    l = draw(s.lists(s.integers(min_value=i)))
    return [i] + l
```

Let's break down what's going on here. First we have the inner function. **The inner function does not return a strategy.** It returns regular Python values. The `@composite` decorator is what converts this function into a strategy. In addition to its usual parameters, the inner function also has a `draw` parameter. Calling this function on a strategy draws a concrete value. We need this because, again, the inner function only returns values, not strategies. We do not explicitly include `draw` when calling the full function; the decorator takes care of that. So we would call this function in a test like:

```py
@given(example())
def test_example(l):
    assert min(l) == l[0]
```

We can do anything we want inside the body of the composite function, making it an exceptionally powerful tool. Here's how we can make sure that our Exam and ExamInstance have the same length:

```py
# Helper function to make the following examples terser
def ei_answers_strategy(exam):
    return s.lists(
        s.one_of(s.none(), s.integers(min_value=1, max_value=5)),
        min_size=len(exam.answer_key),
        max_size=len(exam.answer_key),
    )

@s.composite
def exam_instance_strategy(draw):
    exam = draw(s.from_type(Exam))
    answers = ei_answers_strategy(exam)
    return ExamInstance(student=1, exam=exam, answers=draw(answers))
```

We use it like any other strategy.

```py
@given(exam_instance_strategy()) #pylint: disable=no-value-for-parameter
def test_6(ei):
    assert len(ei.answers) == len(ei.exam.answer_key)
```

(Pylint might complain at you here since we're not passing in an argument for `draw`. There's no actual bug; the `@composite` decorator handles that argument. You can disable the warning by adding `# pylint: disable=no-value-for-parameter` to the line.)

### More with `composite`

Composite strategies are just functions and can be called in other strategies. This means you can use it to create complex connected data. Let's say we want to generate several `ExamInstances` for the same student and exam. We can break this into several composable pieces:

```py
@s.composite
def exam_instance_for_exam(draw, exam, student=""):
    answers = ei_answers_strategy(exam)
    return ExamInstance(student=student, exam=exam, answers=draw(answers))

@s.composite
def many_exam_instances(draw, student=""):
    exam = draw(s.from_type(Exam))
    exams = s.lists(exam_instance_for_exam(exam, student), min_size=1)
    return draw(exams)

@given(many_exam_instances("brian"))
def test_7(eis):
    ...
```

In this case we're only passing raw values into the composite. This means we can't randomize the name of the student. In some cases this is an advantage, as it restricts the state space we have to search. In other cases this is a disadvantage, as it  goes against the spirit of property testing. If you want the more thorough testing, you can pass in strategies instead into the composite and draw values in the body of the function.

```py
@s.composite
def exam_instance_for_exam(draw, exam, student=s.just("")):
    student = draw(student)
    exam = draw(exam)
    answers = ei_answers_strategy(exam)
    return ExamInstance(student=student, exam=exam, answers=draw(answers))

# many_exam_instances is the same... for now

```

There's a usability problem with this, though. Imagine we have `many_exam_instances` pass in complex strategies for `exam` and `student`. How do we know what values we drew? In this _particular_ case we can extract them from the returned ExamInstance, but we can't always rely on that, especially if we do more complex transformations. For this reason it's usually a good idea to pass back all the draws from the composite.

```diff
@s.composite
def exam_instance_for_exam(draw, exam, student=s.just("")):
-  return ExamInstance(student=student, exam=exam, answers=draw(answers))
+  return exam, student, ExamInstance(student=student, exam=exam, answers=draw(answers))
```

We also have to adjust `many_exam_instances` and our test. In particular we can't use the `lists` strategy anymore, as that assumed `exam_instance_for_exam` only returned an ExamInstance. Now that we're returning a tuple of data it gets a bit messier.

```py
@s.composite
def many_exam_instances(draw, student=s.just("")):
    number = draw(s.integers(min_value=1, max_value=5))
    exam = draw(s.from_type(Exam))
    student = draw(student)
    instances = []

    # Getting the values in a loop
    for _ in range(number):
        ei_strategy = exam_instance_for_exam(exam=s.just(exam), student=s.just(student))
        _, _, ei = draw(ei_strategy)
        instances.append(ei)
    return number, exam, student, instances

@given(many_exam_instances(student=s.characters()))
def test_8(stuff):
    _, exam, _, eis = stuff
    ...
```

As you can see, this leads to a lot more boilerplate. We also had to change from using the `lists` strategy to using a loop, which is slower and less clear. Whether the tradeoffs are worth it depends on your specific case.[^compromise]

[^compromise]: A good compromise is to have the "root" composite take strategies and all its helper strategies take raw values.

## `data`

The last way to generate complex inputs is the `data` strategy. Like `composite`, it gives us a `draw` function that we can use to interactively pick values. Unlike `composite`, we can use it in the test body! Instead of `exam_instance_strategy`, we can do this instead:

```py
@given(s.data(), s.from_type(Exam))
def test_data(data, exam):
    answers = data.draw(ei_answers_strategy(exam))

    ei = ExamInstance(student=1, exam=exam, answers=answers)
    assert len(ei.answers) == len(ei.exam.answer_key)
```

The main benefit of `data` is that you can customize your strategy based on the behavior inside the test. Something like:

```py
if f(x):
    y = data.draw(st.integers(min_value=1, max_value=10))
else:
    y = data.draw(st.integers(min_value=6, max_value=20))
```

The downside is that `data` doesn't play well with other Hypothesis features, like examples and error reporting. If you can generate all your data ahead of time then you're better off using composites.

## Summary

Hypothesis can infer a lot using `from_type`. If most random inputs are valid and you just need to rule out rare edge cases, then `assume` and `filter` are simple and effective. Past that, you can use `builds` to generate data with complex invariants. The `composite` strategy gives you even more control and lets you relate multiple draws to each other, making it possible to create lots of interdependent data. Finally, the `data` strategy lets you interactively pick values in the test itself. And all custom strategies can be associated with a type via `register_type_strategy`.

Hypothesis provides a lot of mechanisms to create complex data. Learning how to use them well is a bit of an art, but well worth it. Hopefully this makes "what to use when" a little more clear.

_Thanks to Zac Hatfield-Dodds and Oskar Wickström for feedback._
