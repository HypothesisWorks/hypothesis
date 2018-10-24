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
