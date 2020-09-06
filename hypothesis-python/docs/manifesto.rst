=========================
The purpose of Hypothesis
=========================

What is Hypothesis for?

From the perspective of a user, the purpose of Hypothesis is to make it easier for
you to write better tests.

From my perspective as the author, that is of course also a purpose of Hypothesis,
but (if you will permit me to indulge in a touch of megalomania for a moment), the
larger purpose of Hypothesis is to drag the world kicking and screaming into a new
and terrifying age of high quality software.

Software is, as they say, eating the world. Software is also `terrible`_. It's buggy,
insecure and generally poorly thought out. This combination is clearly a recipe for
disaster.

And the state of software testing is even worse. Although it's fairly uncontroversial
at this point that you *should* be testing your code, can you really say with a straight
face that most projects you've worked on are adequately tested?

A lot of the problem here is that it's too hard to write good tests. Your tests encode
exactly the same assumptions and fallacies that you had when you wrote the code, so they
miss exactly the same bugs that you missed when you wrote the code.

Meanwhile, there are all sorts of tools for making testing better that are basically
unused. The original Quickcheck is from *1999* and the majority of developers have
not even heard of it, let alone used it. There are a bunch of half-baked implementations
for most languages, but very few of them are worth using.

The goal of Hypothesis is to bring advanced testing techniques to the masses, and to
provide an implementation that is so high quality that it is easier to use them than
it is not to use them. Where I can, I will beg, borrow and steal every good idea
I can find that someone has had to make software testing better. Where I can't, I will
invent new ones.

Quickcheck is the start, but I also plan to integrate ideas from fuzz testing (a
planned future feature is to use coverage information to drive example selection, and
the example saving database is already inspired by the workflows people use for fuzz
testing), and am open to and actively seeking out other suggestions and ideas.

The plan is to treat the social problem of people not using these ideas as a bug to
which there is a technical solution: Does property-based testing not match your workflow?
That's a bug, let's fix it by figuring out how to integrate Hypothesis into it.
Too hard to generate custom data for your application? That's a bug. Let's fix it by
figuring out how to make it easier, or how to take something you're already using to
specify your data and derive a generator from that automatically. Find the explanations
of these advanced ideas hopelessly obtuse and hard to follow? That's a bug. Let's provide
you with an easy API that lets you test your code better without a PhD in software
verification.

Grand ambitions, I know, and I expect ultimately the reality will be somewhat less
grand, but so far in about three months of development, Hypothesis has become the most
solid implementation of Quickcheck ever seen in a mainstream language (as long as we don't
count Scala as mainstream yet), and at the same time managed to
significantly push forward the state of the art, so I think there's
reason to be optimistic.

.. _terrible: https://www.youtube.com/watch?v=csyL9EC0S0c
