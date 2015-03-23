===================
History and lineage
===================

The type of testing Hypothesis does is called property based testing, though
Hypothesis deliberately blurs the lines between property based testing and more
standard unit testing.

The idea was popularised by a Haskell library called `Quickcheck
<https://wiki.haskell.org/Introduction_to_QuickCheck2>`_, and has since been
ported to many different languages. The most recent ancestor
of Hypothesis is `ScalaCheck <http://scalacheck.org/>`_, in the sense that this is
the Quickcheck port I had used the most before writing it, but there are
sufficiently many differences that Hypothesis isn't really any closer to being a
port of Scalacheck than it is a port of Quickcheck.

Most quickcheck ports are very disappointing: Poor quality of data generation,
failure to do example minimization, difficult to extend, etc. Even a bad
version of quickcheck is still better than nothing, but Hypothesis aims to be
a *lot* better than that. It's a production quality implementation, with a
number of interesting innovations not previously found in any other
implementations.
