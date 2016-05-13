---
layout: post
tags: technical python details
date: 2016-05-11 10:00
title: Generating the right data
published: true
---

One thing that often causes people problems is figuring out how to generate
the right data to fit their data
model. You can start with just generating strings and integers, but eventually you want
to be able to generate
objects from your domain model. Hypothesis provides a lot of tools to help you build the
data you want, but sometimes the choice can be a bit overwhelming.

Here's a worked example to walk you through some of the details and help you get to grips with how to use
them.

<!--more-->

Suppose we have the following class:

```python

class Project(object):
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end

    def __repr__(self):
      return "Project '%s from %s to %s" % (
        self.name, self.start.isoformat(), self.end.isoformat()
      )
```

A project has a name, a start date, and an end date.

How do we generate such a thing?

The idea is to break the problem down into parts, and then use the tools
Hypothesis provides to assemble those parts into a strategy for generating
our projects.

We'll start by generating the data we need for each field, and then at the end
we'll see how to put it all together to generate a Project.

### Names

First we need to generate a name. We'll use Hypothesis's standard text
strategy for that:

```pycon
>>> from hypothesis.strategies import text
>>> text().example()
''
>>> text().example()
'\nŁ昘迥'
```

Lets customize this a bit: First off, lets say project names have to be
non-empty.

```pycon
>>> text(min_size=1).example()
'w\nC'
>>> text(min_size=1).example()
'ሚಃJ»'
```

Now, lets avoid the high end unicode for now (of course, your system *should*
handle the full range of unicode, but this is just an example, right?).

To do this we need to pass an alphabet to the text strategy. This can either be
a range of characters or another strategy. We're going to use the *characters*
strategy, which gives you a flexible way of describing a strategy for single-character
text strings, to do that.

```pycon
i>>> characters(min_codepoint=1, max_codepoint=1000, blacklist_categories=('Cc', 'Cs')).example()
'²'
>>> characters(min_codepoint=1, max_codepoint=1000, blacklist_categories=('Cc', 'Cs')).example()
'E'
>>> characters(min_codepoint=1, max_codepoint=1000, blacklist_categories=('Cc', 'Cs')).example()
'̺'

```

The max and min codepoint parameters do what you'd expect: They limit the range of
permissible codepoints. We've blocked off the 0 codepoint (it's not really useful and
tends to just cause trouble with C libraries) and anything with a codepoint above
1000 - so we're considering non-ASCII characters but nothing really high end.

The blacklist\_categories parameter uses the notion of [unicode category](https://en.wikipedia.org/wiki/Unicode_character_property#General_Category)
to limit the range of acceptable characters. If you want to see what category a
character has you can use Python's unicodedata module to find out:

```pycon
>>> from unicodedata import category
>>> category('\n')
'Cc'
>>> category('\t')
'Cc'
>>> category(' ')
'Zs'
>>> category('a')
'Ll'
```

The categories we've excluded are *control characters* and *surrogates*. Surrogates
are excluded by default but when you explicitly pass in blacklist categories you
need to exclude them yourself.

So we can put that together with text() to get a name matching our requirements:

```pycon
>>> names = text(characters(max_codepoint=1000, blacklist_categories=('Cc', 'Cs')), min_size=1)
```

But this is still not quite right: We've allowed spaces in names, but we don't really want
a name to start with or end with a space. You can see that this is currently allowed by
asking Hypothesis for a more specific example:

```pycon
>>> find(names, lambda x: x[0] == ' ')
' '
```

So lets fix it so that they can't by stripping the spaces off it.

To do this we're going to use the strategy's *map* method which lets you compose it with
an arbitrary function to post-process the results into the for you want:

```pycon
>>> names = text(characters(max_codepoint=1000, blacklist_categories=('Cc', 'Cs')), min_size=1).map(
...     lambda x: x.strip())
```

Now lets check that we can no longer have the above problem:

```pycon
>>> find(names, lambda x: x[0] == ' ')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3.5/site-packages/hypothesis/core.py", line 648, in find
    runner.run()
  File "/usr/lib/python3.5/site-packages/hypothesis/internal/conjecture/engine.py", line 168, in run
    self._run()
  File "/usr/lib/python3.5/site-packages/hypothesis/internal/conjecture/engine.py", line 262, in _run
    self.test_function(data)
  File "/usr/lib/python3.5/site-packages/hypothesis/internal/conjecture/engine.py", line 68, in test_function
    self._test_function(data)
  File "/usr/lib/python3.5/site-packages/hypothesis/core.py", line 616, in template_condition
    success = condition(result)
  File "<stdin>", line 1, in <lambda>
IndexError: string index out of range
```

Whoops!

The problem is that our initial test worked because the strings we were generating were always
non-empty because of the min\_size parameter. We're still only generating non-empty strings,
but if we generate a string which is all spaces then strip it, the result will be empty
*after* our map.

We can fix this using the strategy's *filter* function, which restricts to only generating
things which satisfy some condition:

```pycon
>>> names = text(characters(max_codepoint=1000, blacklist_categories=('Cc', 'Cs')), min_size=1).map(
...     lambda s: s.strip()).filter(lambda s: len(s) > 0)
```

And repeating the check:

```pycon
>>> find(names, lambda x: x[0] == ' ')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3.5/site-packages/hypothesis/core.py", line 670, in find
    raise NoSuchExample(get_pretty_function_description(condition))
hypothesis.errors.NoSuchExample: No examples found of condition lambda x: <unknown>
```

Hypothesis raises NoSuchExample to indicate that... well, that there's no such example.

In general you should be a little bit careful with filter and only use it to filter
to conditions that are relatively hard to happen by accident. In this case it's fine
because the filter condition only fails if our initial draw was a string consisting
entirely of spaces, but if we'd e.g. tried the opposite and tried to filter to strings
that *only* had spaces, we'd have had a bad time of it and got a very slow and not
very useful test.

Anyway, we now really do have a strategy that produces decent names for our projects.
Lets put this all together into a test that demonstrates that our names now have the
desired properties:

```python
from hypothesis.strategies import characters, text
from hypothesis import given
from unicodedata import category


names = text(
    characters(max_codepoint=1000, blacklist_categories=('Cc', 'Cs')),
    min_size=1).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

@given(names)
def test_names_match_our_requirements(name):
    assert len(name) > 0
    assert name == name.strip()
    for c in name:
        assert 1 <= ord(c) <= 1000
        assert category(c) not in ('Cc', 'Cs')
```

It's not common practice to write tests for your strategies, but it can be helpful
when trying to figure things out.

### Dates and times

Hypothesis has date and time generation in a hypothesis.extra subpackage because it
relies on pytz to generate them, but other than that it works in exactly the same
way as before:

```pycon
>>> from hypothesis.extra.datetime import datetimes
>>> datetimes().example()
datetime.datetime(1642, 1, 23, 2, 34, 28, 148985, tzinfo=<DstTzInfo 'Antarctica/Mawson' zzz0:00:00 STD>)
```

Lets constrain our dates to be UTC, because the sensible thing to do is to use UTC
internally and convert on display to the user:

```pycon
>>> datetimes(timezones=('UTC',)).example()
datetime.datetime(6820, 2, 4, 19, 16, 27, 322062, tzinfo=<UTC>)
```

We can also constrain our projects to start in a reasonable range of years,
as by default Hypothesis will cover the whole of representable history:

```pycon
>>> datetimes(timezones=('UTC',), min_year=2000, max_year=2100).example()
datetime.datetime(2084, 6, 9, 11, 48, 14, 213208, tzinfo=<UTC>)
```

Again we can put together a test that checks this behaviour (though we have
less code here so it's less useful):

```python

from hypothesis import given
from hypothesis.extra.datetime import datetimes

project_date = datetimes(timezones=('UTC',), min_year=2000, max_year=2100)


@given(project_date)
def test_dates_are_in_the_right_range(date):
    assert 2000 <= date.year <= 2100
    assert date.tzinfo._tzname == 'UTC'
```

### Putting it all together

We can now generate all the parts for our project definitions, but how do we
generate a project?

The first thing to reach for is the *builds* function.

```pycon

>>> from hypothesis.strategies import builds
>>> projects = builds(Project, name=names, start=project_date, end=project_date)
>>> projects.example()
Project 'd!#ñcJν' from 2091-06-22T06:57:39.050162+00:00 to 2057-06-11T02:41:43.889510+00:00
```

builds lets you take a set of strategies and feed their results as arguments to a
function (or, in this case, class. Anything callable really) to create a new
strategy that works by drawing those arguments then passing them to the function
to give you that example.

Unfortunately, this isn't quite right:

```pycon
>>> find(projects, lambda x: x.start > x.end)
Project '0' from 2000-01-01T00:00:00.000001+00:00 to 2000-01-01T00:00:00+00:00
``` 

Projects can start after they end when we use builds this way. One way to fix this would be
to use filter():

```pycon
>>> projects = builds(Project, name=names, start=project_date, end=project_date).filter(
...     lambda p: p.start < p.end)
>>> find(projects, lambda x: x.start > x.end)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3.5/site-packages/hypothesis/core.py", line 670, in find
    raise NoSuchExample(get_pretty_function_description(condition))
hypothesis.errors.NoSuchExample: No examples found of condition lambda x: <unknown>
```

This will work, but it starts to edge into the territory of where filter should be
avoided - about half of the initially generated examples will fail the filter.

What we'll do instead is draw two dates and use whichever one is smallest as the
start, and whatever is largest at the end. This is hard to do with builds because
of the dependence between the arguments, so instead we'll use builds' more advanced
cousin, *composite*:

```python
from hypothesis.strategies import composite
from hypothesis import assume

@composite
def projects(draw):
    name = draw(names)
    date1 = draw(project_date)
    date2 = draw(project_date)
    assume(date1 != date2)
    start = min(date1, date2)
    end = max(date1, date2)
    return Project(name, start, end)
```

The idea of composite is you get passed a magic first argument 'draw' that you can
use to get examples out of a strategy. You then make as many draws as you want and
use these to return the desired data.

You can also use the *assume* function to discard the current call if you get yourself
into a state where you can't proceed or where it's easier to start again. In this case
we do that when we draw the same data twice.

```pycon
>>> projects().example()
Project 'rĂ5ĠǓ#' from 2000-05-14T07:21:12.282521+00:00 to 2026-05-12T13:20:43.225796+00:00
>>> find(projects(), lambda x: x.start > x.end)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3.5/site-packages/hypothesis/core.py", line 670, in find
    raise NoSuchExample(get_pretty_function_description(condition))
hypothesis.errors.NoSuchExample: No examples found of condition lambda x: <unknown>
```

Note that in all of our examples we're now writing projects() instead of projects. That's
because composite returns a function rather than a strategy. Any arguments to your
defining function other than the first are also arguments to the one produced by composite.

We can now put together one final test that we got this bit right too:

```python
@given(projects())
def test_projects_end_after_they_started(project):
    assert project.start < project.end
```

### Wrapping up

There's a lot more to Hypothesis's data generation than this, but hopefully it gives you
a flavour of the sort of things to try and the sort of things that are possible.

It's worth having a read of [the documentation](http://hypothesis.readthedocs.io/en/latest/data.html)
for this, and if you're still stuck then try asking [the community](http://hypothesis.readthedocs.io/en/latest/community.html)
for some help. We're pretty friendly.


