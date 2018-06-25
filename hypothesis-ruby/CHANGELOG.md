# Hypothesis for Ruby 0.0.14 (2018-06-25)

This release updates the release date to the correct date, as part of fixing a
bug which caused the last couple of releases (0.0.11, 0.0.12, and 0.0.13) to
have an incorrect date.

# Hypothesis for Ruby 0.0.13 (2018-06-25)

This release moves the core Rust engine into the separate Conjecture crate. It
should have no user visible effect.

# Hypothesis for Ruby 0.0.12 (2018-06-23)

This release is the beginning of splitting out the Rust core of Hypothesis
Ruby into a separate `conjecture` crate for the non-Ruby-specific components
of it.

It should have no user visible impact.

# Hypothesis for Ruby 0.0.11 (2018-06-22)

This release has no user-visible changes other than updating the gemspec's
homepage attribute.

## Hypothesis for Ruby 0.0.10 (2018-04-26)

This release is another update to shrinking:

* Cases where the value may be simplified without necessarily
  becoming smaller will have better results.
* Duplicated values can now sometimes be simultaneously shrunk.

## Hypothesis for Ruby 0.0.9 (2018-04-20)

This improves Hypothesis for Ruby's shrinking to be much closer
to Hypothesis for Python's. It's still far from complete, and even
in cases where it has the same level of quality it will often be
significantly slower, but examples should now be much more consistent,
especially in cases where you are using e.g. `built_as`.

## Hypothesis for Ruby 0.0.8 (2018-02-20)

This release fixes the dependency on Rake to be in a more sensible range.

## Hypothesis for Ruby 0.0.7 (2018-02-19)

This release updates an error in the README.

## Hypothesis for Ruby 0.0.6 (2018-02-19)

This release just updates the gem description.

## Hypothesis for Ruby 0.0.5 (2018-02-19)

This is a trivial release to test the release automation.
It should have no user visible impact.

## Hypothesis for Ruby 0.0.3 (2018-02-19)

This is an initial developer preview of Hypothesis for Ruby.
It's ready to use, but isn't yet stable and has significant
limitations. It is mostly released so that people can easily give
feedback on the API and implementation, and is likely to change
substantially before a stable release.

Note that while there were some earlier release numbers internally,
these were pulled. This is the first official release.
