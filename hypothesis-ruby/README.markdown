# Hypothesis for Ruby

Hypothesis is a powerful, flexible, and easy to use library for *property-based testing*.

In property-based testing,
in contrast to traditional *example-based testing*,
a test is written not against a single example but as a statement that should hold for any of a range of possible values.

## Usage

In Hypothesis for Ruby, a test looks something like this:

```ruby
require "hypothesis"

RSpec.configure do |config|
  config.include(Hypothesis)
  config.include(Hypothesis::Possibilities)
end

RSpec.describe "removing an element from a list" do
  it "results in the element no longer being in the list" do
    hypothesis do
      # Or lists(of: integers, min_size: 1), but this lets us
      # demonstrate assume.
      values = any array(of: integers)

      # If this is not true then the test will stop here.
      assume values.size > 0

      to_remove = any element_of(values)

      values.delete_at(values.index(to_remove))

      # Will fail if the value was duplicated in the list.
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

The use of RSpec here is incidental:
Hypothesis for Ruby works just as well with minitest,
and should work with anything else you care to use.

## Getting Started

Hypothesis is available on rubygems.org as a developer preview.
If you want to try it today you can use the current development branch by adding the following to your Gemfile:

```ruby
gem 'hypothesis-specs'
```

The API is still in flux, so be warned that you should expect it to break on upgrades!
Right now this is really more to allow you to try it out and provide feedback than something you should expect to rely on.
The more feedback we get, the sooner it will get there!

Note that in order to use Hypothesis for Ruby, you will need a rust toolchain installed.
Please go to [https://www.rustup.rs](https://www.rustup.rs) and follow the instructions if you do not already have one. You will most likely need to compile your Ruby executable with the `--enable-shared` option. See [here](https://github.com/danielpclark/rutie#dynamic-vs-static-builds).

## Project Status

Hypothesis for Ruby is currently in an *early alpha* stage.
It works, and has a solid core set of features, but you should expect to find rough edges,
it is far from feature complete, and the API makes no promises of backwards compatibility.

Right now you should consider it to be more in the spirit of a developer preview.
You can and should try it out, and hopefully you will find all sorts of interesting bugs in your code by doing so!
But you'll probably find interesting bugs in Hypothesis too,
and we'd appreciate you reporting them,
as well as any just general usability issues or points of confusion you have.
