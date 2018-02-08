# Usage

This is a very small set of narrative documentation about
how to use the Hypothesis for Ruby API. It is in no way
complete, but is here as a kind of place holder to give
you enough information to get started and to make me
write down enough to make sure that the thing I'm describing
isn't actually a bad idea.

## Core Concepts

When writing a test using Hypothesis, you have three things:

* The hypothesis you are testing
* A set of "givens" - values that are required for you to
  run the test.
* A set of "assumptions" - things that need to be true in
  order for the test to be valid.

The givens come from *providers*, which describe a range of
values that you can use in testing. Hypothesis provides a
large number of built in methods for constructing providers,
including ones that let you chain things together to define
your own.

## Usage

A test looks something like this:

```ruby
require "hypothesis"

RSpec.configure do |config|
  config.include(Hypothesis)
  config.include(Hypothesis::Providers)
end

RSpec.describe "removing an element from a list" do
  it "results in the element no longer being in the list" do
    hypothesis do
      # Or lists(integers, min_size: 1), but this lets us
      # demonstrate assume.
      values = given lists(integers)

      # If this is not true then the test will stop here.
      assume values.length > 0

      # note: choice_of is not currently implemented, but
      # would provide any value chosen from its argument.
      to_remove = given(choice_of(values))

      values.delete_at(value.index(to_remove))

      # Will fail if the value ws duplicated in the list.
      expect(values.include?(to_remove)).to be false
      
    end
  end
end
```

This would then fail with:

```
  1) removing an element from a list results in the element no longer being in the list
     Failure/Error: expect(values.include?(to_remove)).to be false

       Given #1: [0, 0]
       Given #2: 0

       expected false
            got true
```

You can also add labels to your givens if you like. For example:

```ruby
RSpec.describe "integer addition" do
  it "increases the size" do
    hypothesis do
      m = given integers, name: 'm'
      n = given integers, name: 'n'
      expect(m + n).to be > m
    end
  end
end
```

When this fails it will attach those names to the values generated:

```
  1) integer addition increases the size
     Failure/Error: expect(m + n).to be > m

       Given m: 0
       Given n: 0

       expected: > 0
            got:   0
```

## Execution Model

The general way you're supposed to pretend this works is that
Hypothesis magically picked exactly the right values to give you to most simply
demonstrate the test failure.

The way this actually works is that hypothesis calls your test block repeatedly
(so in particular any side effects in it will be run multiple times. Make sure
your test set up and tear down happens inside the block!) until it finds a
failing set of givens, and then will try to reduce those givens down to the
simplest set that triggers a failure.

## Defining your own providers

The library of providers you get from Hypothesis is large but finite.
At some point you're going to want something it doesn't include - e.g. to
construct your own data types.

You can do this using the composite provider:

```ruby
module MyProviders
  include Hypothesis::Providers

  def names
    strings min_size: 1, max_size: 10 
  end

  def users 
    composite do |source|
      User.new(
        name: source.given names,
        age: source.given integers(
          min_value: 0, max_value: 100)
      )
    end
  end
end
```

Note: We don't currently have parameters to strings, and there's
no integers provider at present, but those will both be things when
the library is mature.

You can now use this just like a built in provider (as long as you
include your module):

```ruby
require "hypothesis"

RSpec.configure do |config|
  config.include(Hypothesis)
  config.include(MyProviders)
end

RSpec.describe User do
  it "has a name" do
    hypothesis do
      expect(given(user).name.length).to be > 0
    end
  end
end
```


composite is given a source object, which is the `self` parameter from
the body of a hypothesis, and returns a value.
That value is will be provided for a given when your composite is used
as its argument.

We may at some point move to supporting `given` and `assume` without
the explicit source parameter, but currently all of the ways of doing
that I've considered are unsatisfying and brittle, so I've adopted the
boring conventional approach of just passing arguments to functions.
