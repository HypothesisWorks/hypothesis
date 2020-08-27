RELEASE_TYPE: patch

This release fixes a bug in some Hypothesis internal support code for learning
automata. This mostly doesn't have any user visible impact, although it slightly
affects the learned shrink passes so shrinking may be subtly different.
