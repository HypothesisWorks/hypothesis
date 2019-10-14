# Design Notes

The current goals of the Hypothesis for Ruby project are:

* To provide a useful but not wholly feature complete version of
  [Hypothesis](https://hypothesis.works/) for Ruby, that works with
  RSpec (and ideally minitest, but if that at any point proves to
  be a lot of work this may be dropped. It's not an explicit
  requirement, but supporting it now makes it much easier to find
  the right shape of the project design).
* To provide a mostly feature complete version of the Conjecture
  engine that powers Hypothesis in Rust, as decoupled from that
  Ruby front-end as possible.

Hypothesis for Ruby is not intended to be an exact feature for
feature copy of the Python version. It will have a lot of the same
underlying functionality, but with a number of changes driven by:

* Trying to make it feel as "ruby native" as possible.
* The ability to design an API from scratch that lacks many of the
  constraints imposed both by the earlier much more limited functionality
  of Hypothesis and the specifics of Python decorators and test
  frameworks.

## Differences

The most fundamental API differences  between Hypothesis
for Python and Hypothesis for Ruby are:

* In Python we do a whole giant song and dance about exposing
  functions for the test runner to call, while in Ruby we just
  have a function which repeatedly calls a block and then fails.
* In Python you specify a bunch of given parameters up front,
  and then if you want values inline in the test you [explicitly
  opt in to it](https://hypothesis.readthedocs.io/en/latest/data.html#drawing-interactively-in-tests),
  while in Ruby this is not only the default but the only way to
  get those values.
* Strategies are called Possibles because strategy is a terrible
  name that was originally intended to be internal and then leaked
  into the public API because I wasn't thinking hard about naming.
* Many of the Possible implementations have different names than
  the corresponding
  names in hypothesis-python. There is also a weird dual naming
  convention for Possibles where there is both e.g. `integers` and
  `integer` as aliases for each other.

So for example:

```ruby
RSPec.describe "integer addition" do
  it "commutes" do
    hypothesis do
      m = any integer
      n = any integer
      expect(m + n).to eq(n + m)
    end
  end
end
```

```python
@given(integers(), integers())
def test_integers_commute(m, n):
    assert m + n == n + m
```

The in-line style is slightly more verbose, but vastly more flexible
and (I think) reads better. Also mixing in-line and up-front
styles looks weird, and if we're going to have just one then
the in-line approach is a strict superset of the functionality
of the other.

The main reason for these differences are:

* Ruby blocks (and their relation to testing) make this approach
  much more natural.
* This functionality was not actually possible when the Hypothesis
  for Python API was originally designed, which informed the way
  its API looks.

## Deliberate omissions

The following are currently *not* part of the intended feature set
of Hypothesis for Ruby:

* Calls to `hypothesis` may not be nested.
* There will be no equivalent to the [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
  (but the very interactive nature of tests in the Ruby API means that
  the generic state machine stuff is just something you can write in
  your normal tests).
* Testing will not be coverage guided (to be fair, it's barely coverage
  guided in the Python version right now...)
* There will probably not be a health check system as part of the initial
  release, or if there is it will be much more basic.
* Any equivalent to [`@reproduce_failure`](https://hypothesis.readthedocs.io/en/latest/reproducing.html#reproducing-an-example-with-with-reproduce-failure)

## Possible omissions

The following will be in this initial project on a "time permitting" basis:
If everything else is going well and we've got plenty of time, I'll do them,
but I'm currently anticipating a tightish schedule so these are probably
for a future release:

* Reporting multiple failing examples per test (this will definitely be supported
  in the core engine, and if it's easy to support it then it will
  also be included in the front-end. I currently think it will be
  easy, but if it's not it will be dropped).
* [adding explicit examples](https://hypothesis.readthedocs.io/en/latest/reproducing.html#providing-explicit-examples).

## Current Project State

The current state is best described as "nascent" - it demonstrates
a lot of the right moving parts, but has rough edges that you will
hit almost immediately if you try to use it. Those rough edges need
to be filed off before it can be built.

Things that don't work yet but will:

* The Possible library is limited, and most of what is there is bad.
* The shrinker is *very* primitive in comparison to in Python.
* The example database does not yet exist.
* It can't actually be installed as a gem! Note that even once it is
  installable you will need a rust compiler and cargo.
