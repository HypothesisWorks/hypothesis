# Conjecture for Rust 0.7.0 (2021-02-01)

This release improves flexibility and performance of `distributions::Sampler::new` by allowing it to accept `&[f32]` instead of a `Vec`.
It also positively affects `distributions::good_bitlengths` as it does not have to allocate a vector anymore.

# Conjecture for Rust 0.6.0 (2021-01-27)

This release is required following an unsuccessful deploy of 0.5.0 due to usage of a cargo keyword that was too long.

# Conjecture for Rust 0.5.0 (2021-01-27)

Adds support for skipping shrinking. While shrinking is extremely helpful and important in general, it has the potential to be quite time consuming. It can be useful to observe a raw failure before choosing to allow the engine to try to shrink. [hypothesis-python](https://hypothesis.readthedocs.io/en/latest/settings.html#phases) already provides the ability to skip shrinking, so there is precedent for this being useful.

Also swaps out the deprecated tempdir crate with tempfile.

# Conjecture for Rust 0.4.0 (2018-10-24)

This release extends Conjecture for Rust with support for saving examples it discovers on disk in an example database,
in line with Hypothesis for Python's existing functionality for this.

# Conjecture for Rust 0.3.0 (2018-07-16)

This release adds support for annotating interesting examples
to indicate that they are logically distinct. When multiple distinct
reasons for being interesting are found, Conjecture will attempt to
shrink all of them.

# Conjecture for Rust 0.2.1 (2018-06-25)

This release fixes an occasional assertion failure that could occur
when shrinking a failing test.

# Conjecture for Rust 0.2.0 (2018-06-25)

This release brings over all of the core code and API that was previously in
hypothesis-ruby.

# Conjecture for Rust 0.1.1 (2018-06-23)

This is an essentially no-op release that just updates the package homepage and
puts this package under the Hypothesis continuous release system.

# Conjecture for Rust 0.1.0 (2018-06-19)

This is an initial empty package release of Conjecture for Rust, solely
to start fleshing out the release system and package dependency architecture
between this and Hypothesis for Ruby. It literally does nothing.
