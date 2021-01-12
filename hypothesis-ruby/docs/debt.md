# A Series of Unfortunate Implementation Choices

## In Which The Narrator Seeks To Justify Himself

This project is currently in a somewhat expeditionary state,
where its goal is not to produce wonderful software that will
stand the test of time, but instead to prove its concept
valid and get something working enough for me to decide
whether it's worth it to continue down this route, and
to decide whether it's worth it to continue funding it.

As such, whenever presented with the question "Do we want it
good or do we want it soon?" I am mostly choosing soon.

BUT I am optimistic about the long-term viability of this
project, and I do not wish to find future-David cursing the
very name of past-David. In aid of squaring this particular
circle, I am choosing to document every terrible thing that
I knowingly do.

The goals of this documentation are:

* To make me feel bad, so that I'm less likely to do things
  that are awful but not actually needed.
* To explain the reasoning to future-me and those who come
  after.
* To make explicit the conditions under which the awful hack
  may be removed.

## Awful Hacks

### Threads as a Control Flow Mechanism

Rather than attempt to encode the generation state machine
explicitly, which was proving to be absolutely awful, I
decided to continue to write it synchronously. The Rust side
of the equation does not control calling the test function,
which makes this tricky (and having the asynchronous interface
as the main API entry point is a long term good anyway).

The ideal way of doing this would be with something lightweight,
like a coroutines. The ideal way of doing coroutines would be
[Rust generators](https://doc.rust-lang.org/nightly/unstable-book/language-features/generators.html).

Unfortunately this suffers from two problems:

* It requires rust nightly. I would be prepared to live with this,
  but it's sub-par.
* The current implementation is one-way only: resume does not take
  an argument.

Alternate things tried: 

* [libfringe](https://github.com/edef1c/libfringe) seems lovely,
  but also requires rust-nightly and the released version doesn't
  actually build on rust nightly
* I didn't really look into [may](https://github.com/Xudong-Huang/may/)
  after a) getting vaguely warned off it and b) Honestly having
  coroutine implementation exhaustion at this point.

So at this point I said "Screw it, threads work on stable, and the
context switching overhead isn't going to be *that* large compared
to all the other mess that's in this chain, so..."

So, yeah, that's why the main loop runs in a separate thread and
communicates with the main thread via a synchronous channel.

Can be removed when one of:

* Generators are on stable and support resuming with an argument.
* libfringe works on stable
* Either of the above but on unstable, and my frustration with
  threading bugs (but fearless concurrency, David!) outweighs
  my desire to not use nightly.

### Stable identifiers from RSpec

Another "I did terrible things to RSpec" entry, sorry. RSpec's
design here is totally reasonable and sensible and honestly
probably *is* how you should pass state around, but seems
to make it impossible to get access to the Example object from
inside an it block without actually being the definer of the
block.

See `hypothesis_stable_identifier` for details, but basically I
couldn't figure out how to get the name of a currently executing
spec in RSPec from a helper function without some fairly brutal
hacks where we extract information badly from self.inspect, because
it's there stored as a string that gets passed in for inspection.

Can be removed when: Someone shows me a better way, or a
feature is added to RSpec to make this easier.
