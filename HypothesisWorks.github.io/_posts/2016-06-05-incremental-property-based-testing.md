---
layout: post
tags: intro python technical properties
date: 2016-06-05 16:00
title: Evolving toward property-based testing with Hypothesis
published: true
author: jml
---

Many people are quite comfortable writing ordinary unit tests, but feel a bit
confused when they start with property-based testing. This post shows how two
ordinary programmers started with normal Python unit tests and nudged them
incrementally toward property-based tests, gaining many advantages on the way.

<!--more-->

Background
----------

I used to work on a command-line tool with an interface much like git's. It
had a repository, and within that repository you could create branches and
switch between them. Let's call the tool tlr

It was supposed to behave something like this:

List branches:

    $ tlr branch
    foo
    * master

Switch to an existing branch:

    $ tlr checkout foo
    * foo
    master

Create a branch and switch to it:

    $ tlr checkout -b new-branch
    $ tlr branch
    foo
    master
    * new-branch

Early on, my colleague and I found a bug: when you created a new branch with
`checkout -b` it wouldn't switch to it. The behavior looked something like
this:

    $ tlr checkout -b new-branch
    $ tlr branch
    foo
    * master
    new-branch

The previously active branch (in this case, `master`) stayed active, rather
than switching to the newly-created branch (`new-branch`).

Before we fixed the bug, we decided to write a test. I thought this would be a
good chance to start using Hypothesis.

Writing a simple test
---------------------

My colleague was less familiar with Hypothesis than I was, so we started with
a plain old Python unit test:

```python
    def test_checkout_new_branch(self):
        """
        Checking out a new branch results in it being the current active
        branch.
        """
        tmpdir = FilePath(self.mktemp())
        tmpdir.makedirs()
        repo = Repository.initialize(tmpdir.path)
        repo.checkout("new-branch", create=True)
        self.assertEqual("new-branch", repo.get_active_branch())
```

The first thing to notice here is that the string `"new-branch"` is not
actually relevant to the test. It's just a value we picked to exercise the
buggy code. The test should be able to pass with *any valid branch name*.

Even before we started to use Hypothesis, we made this more explicit by making
the branch name a parameter to the test:

```python
    def test_checkout_new_branch(self, branch_name="new-branch"):
        tmpdir = FilePath(self.mktemp())
        tmpdir.makedirs()
        repo = Repository.initialize(tmpdir.path)
        repo.checkout(branch_name, create=True)
        self.assertEqual(branch_name, repo.get_active_branch())
```

(For brevity, I'll elide the docstring from the rest of the code examples)

We never manually provided the `branch_name` parameter, but this change made
it more clear that the test ought to pass regardless of the branch name.

Introducing Hypothesis
----------------------

Once we had a parameter, the next thing was to use Hypothesis to provide the
parameter for us. First, we imported Hypothesis:

```python
    from hypothesis import given
    from hypothesis import strategies as st
```

And then made the simplest change to our test to actually use it:

```python
    @given(branch_name=st.just("new-branch"))
    def test_checkout_new_branch(self, branch_name):
        tmpdir = FilePath(self.mktemp())
        tmpdir.makedirs()
        repo = Repository.initialize(tmpdir.path)
        repo.checkout(branch_name, create=True)
        self.assertEqual(branch_name, repo.get_active_branch())
```

Here, rather than providing the branch name as a default argument value, we
are telling Hypothesis to come up with a branch name for us using the
`just("new-branch")`
[strategy](http://hypothesis.readthedocs.io/en/latest/data.html). This
strategy will always come up with `"new-branch"`, so it's actually no
different from what we had before.

What we actually wanted to test is that any valid branch name worked. We
didn't yet know how to generate any valid branch name, but using a
time-honored tradition we pretended that we did:

```python
    def valid_branch_names():
        """Hypothesis strategy to generate arbitrary valid branch names."""
        # TODO: Improve this strategy.
        return st.just("new-branch")

    @given(branch_name=valid_branch_names())
    def test_checkout_new_branch(self, branch_name):
        tmpdir = FilePath(self.mktemp())
        tmpdir.makedirs()
        repo = Repository.initialize(tmpdir.path)
        repo.checkout(branch_name, create=True)
        self.assertEqual(branch_name, repo.get_active_branch())
```

Even if we had stopped here, this would have been an improvement. Although the
Hypothesis version of the test doesn't have any extra power over the vanilla
version, it is more explicit about what it's testing, and the
`valid_branch_names()` strategy can be re-used by future tests, giving us a
single point for improving the coverage of many tests at once.

Expanding the strategy
----------------------

It's only when we get Hypothesis to start generating our data for us that we
really get to take advantage of its bug finding power.

The first thing my colleague and I tried was:

```python
    def valid_branch_names():
        return st.text()
```

But that failed pretty hard-core.

Turns out branch names were implemented as symlinks on disk, so valid branch
name has to be a valid file name on whatever filesystem the tests are running
on. This at least rules out empty names, `"."`, `".."`, very long names, names
with slashes in them, and probably others (it's actually
[really complicated](https://en.wikipedia.org/wiki/Filename#Comparison_of_filename_limitations)).

Hypothesis had made something very clear to us: neither my colleague nor I
actually knew what a valid branch name should be. None of our interfaces
documented it, we had no validators, no clear ideas for rendering & display,
nothing. We had just been assuming that people would pick good, normal,
sensible names.

It was as if we had suddenly gained the benefit of extensive real-world
end-user testing, just by calling the right function. This was:

 1. Awesome. We've found bugs that our users won't.
 2. Annoying. We really didn't want to fix this bug right now.

In the end, we compromised and implemented a relatively conservative strategy
to simulate the good, normal, sensible branch names that we expected:

```python
    from string import letters

    def valid_branch_names():
        # TODO: Handle unicode / weird branch names by rejecting them early, raising nice errors
        # TODO: How do we handle case-insensitive file systems?
        return st.text(
            alphabet=letters, min_size=1, max_size=112).map(lambda t: t.lower())
```

Not ideal, but *much* more extensive than just hard-coding `"new-branch"`, and
much clearer communication of intent.

Adding edge cases
-----------------

There's one valid branch name that this strategy *could* generate, but
probably won't: `master`. If we left the test just as it is, then one time in
a hojillion the strategy would generate `"master"` and the test would fail.

Rather than waiting on chance, we encoded this in the `valid_branch_names`
strategy, to make it more likely:

```python
    def valid_branch_names():
        return st.text(
            alphabet=letters, min_size=1, max_size=112).map(lambda t: t.lower()) | st.just("master")
```

When we ran the tests now, they failed with an exception due to the branch
`master` already existing. To fix this, we used `assume`:

```python
    from hypothesis import assume

    @given(branch_name=valid_branch_names())
    def test_checkout_new_branch(self, branch_name):
        assume(branch_name != "master")
        tmpdir = FilePath(self.mktemp())
        tmpdir.makedirs()
        repo = Repository.initialize(tmpdir.path)
        repo.checkout(branch_name, create=True)
        self.assertEqual(branch_name, repo.get_active_branch())
```

Why did we add `master` to the valid branch names if we were just going to
exclude it anyway? Because when other tests say "give me a valid branch name",
we want *them* to make the decision about whether `master` is appropriate or
not. Any future test author will be compelled to actually think about whether
handling `master` is a thing that they want to do. That's one of the great
benefits of Hypothesis: it's like having a rigorous design critic in your
team.

Going forward
-------------

We stopped there, but we need not have. Just as the test should have held for
any branch, it should also hold for any repository. We were just creating an
empty repository because it was convenient for us.

If we were to continue, the test would have looked something like this:

```python
    @given(repo=repositories(), branch_name=valid_branch_names())
    def test_checkout_new_branch(self, repo, branch_name):
        """
        Checking out a new branch results in it being the current active
        branch.
        """
        assume(branch_name not in repo.get_branches())
        repo.checkout(branch_name, create=True)
        self.assertEqual(branch_name, repo.get_active_branch())
```

This is about as close to a bona fide "property" as you're likely to get in
code that isn't a straight-up computer science problem: if you create and
switch to a branch that doesn't already exist, the new active branch is the
newly created branch.

We got there not by sitting down and thinking about the properties of our
software in the abstract, nor by necessarily knowing much about property-based
testing, but rather by incrementally taking advantage of features of Python
and Hypothesis until our code. On the way, we discovered and, umm, contained a
whole class of bugs, and we made sure that all future tests would be heaps
more powerful. Win.
