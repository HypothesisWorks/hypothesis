---
tags: alternatives, technical
date: 2016-04-16 15:00
title: QuickCheck in Every Language
author: drmaciver
---

<p>
There are a lot of ports of <a href="https://en.wikipedia.org/wiki/QuickCheck">QuickCheck</a>,
the original property based testing library, to a variety of different languages.
</p>

<p>
Some of them are good. Some of them are <em>very</em> good. Some of them are OK. Many are not.
</p>

<p>
I thought it would be worth keeping track of which are which, so I've put together a list.
</p>

<!--more-->

<p>In order to make it onto this list, an implementation has to meet the following criteria:</p>

<ol>
	<li>Must support random generation of data to a test function. e.g. testing systems based on
      <a href="https://hackage.haskell.org/package/smallcheck">smallcheck</a> while interesting and related
      don't fit on this list.
  </li>
	<li>It must be fairly straightforward to generate your own custom types.</li>
	<li>It must support shrinking of falsifying examples.</li>
	<li>It must be under active development, in the sense that bugs in it will get fixed.</li>
	<li>Must be under an OSI approved license.</li>
</ol>
<p>
In this I've tried to to collect a list of what I think the best ones are for any given language.
I haven't used all of these, but I've used some and read and talked to people about the others.
</p>

<h2>Uncontested Winners by Language</h2>

<p>For many languages there is a clear winner that you should just use. Here are the ones I've
found and what I think of them.</p>


<table class="table">

<thead>
<tr>
<th>Language</th>
<th>Library</th>
<th>Our rating</th>
</tr>
</thead>
<tbody>
<tr>
<td>C</td>
<td><a href="https://github.com/silentbicycle/theft">theft</a></td>
<td>Good but does not come with a library of data generators.</td>
</tr>
<tr>
<td>C++</td>
<td><a href="https://github.com/grogers0/CppQuickCheck">CppQuickCheck</a></td>
<td>Unsure</td>
</tr>
<tr>
<td>Clojure</td>
<td><a href="https://github.com/clojure/test.check">test.check</a></td>
<td>Very good</td>
</tr>
<tr>
<td>Coq</td>
<td><a href=https://github.com/QuickChick/QuickChick>QuickChick</a></td>
<td>Unsure</td>
</tr>
<tr>
<td>F#</td>
<td><a href="https://github.com/fscheck/FsCheck">FsCheck</a></td>
<td>Very Good</td>
</tr>
<tr>
<td>Go</td>
<td><a href="https://github.com/leanovate/gopter">gopter</a></td>
<td>Unsure but looks promising.</td>
</tr>
<tr>
<td>Haskell</td>
<td><a href="https://hackage.haskell.org/package/hedgehog">Hedgehog</a></td>
<td>Comparatively new, but looks solid. See below.</td>
</tr>
<tr>
<td>Java</td>
<td><a href="https://github.com/NCR-CoDE/QuickTheories">QuickTheories</a></td>
<td>Unsure. Extremely new but looks promising.</td>
</tr>
<tr>
<td>JavaScript</td>
<td><a href="https://github.com/jsverify/jsverify">jsverify</a></td>
<td>Good</td>
</tr>
<tr>
<td>PHP</td>
<td><a href="https://github.com/giorgiosironi/eris">Eris</a></td>
<td>Unsure. Looks promising.</td>
</tr>
<tr>
<td>Python</td>
<td><a href="http://hypothesis.works">Hypothesis</a></td>
<td>I may be a bit biased on this one, but it's also unambiguously true.</td>
</tr>
<tr>
<td>Ruby</td>
<td><a href="https://github.com/abargnesi/rantly">Rantly</a></td>
<td>Unsure. We're not convinced, but the alternatives are definitely worse.</td>
</tr>
<tr>
<td>Rust</td>
<td><a href="https://github.com/BurntSushi/quickcheck">Quickcheck</a></td>
<td>Unsure, but probably very good based on initial appearance and usage level.</td>
</tr>
<tr>
<td>Scala</td>
<td><a href="https://www.scalacheck.org/">ScalaCheck</a></td>
<td>Very Good</td>
</tr>
<tr>
<td>Swift</td>
<td><a href="https://github.com/typelift/SwiftCheck">Swiftcheck</a></td>
<td>Unsure</td>
</tr>
</tbody>
</table>

<p>Where when I've said "Unsure" I really just mean that I think it looks good but
I haven't put in the depth of in time to be sure, not that I have doubts.</p>

<h2>Special case: Haskell</h2>

<p>
  <a href="https://hackage.haskell.org/package/QuickCheck">The original QuickCheck</a>
  was of course written in Haskell, so it may seem odd that it's not the property based testing
  library I recommend for Haskell!
</p>

<p>
  The reason is that I feel that the design of classic QuickCheck is fundamentally limiting,
  and that Hedgehog takes it in the direction that the rest of the property-based testing
  world is moving (and where most of the implementations for dynamic languages, Hypothesis
  included, already are). In particular its approach starts from generators rather than
  type classes, and it has <a href="../integrated-shrinking %}">integrated shrinking</a>,
  and a fairly comprehensive library of generators.
</p>

<h2>Special case: Erlang</h2>

<p>
  Erlang is a special case because they have <a href="http://www.quviq.com/">QuviQ's QuickCheck</a>.
  Their QuickCheck implementation is by all accounts <em>extremely</em> good, but it is also proprietary
  and fairly expensive. Nevertheless, if you find yourselves in the right language, circumstance and
  financial situation to use it, I would strongly recommend doing so.
</p>

<p>
  In particular, QuviQ's QuickCheck is really the only implementation in this article I think is
  simply better than Hypothesis. Hypothesis is significantly more user friendly, especially if the
  users in question are less than familiar with Erlang, but there are things QuviQ can do that
  Hypothesis can't, and the data generation has had a great deal more engineering effort put into it.
</p>

<p>
  If you're using Erlang but <em>not</em> able to pay for QuickCheck, apparently the one to use is
  <a href="https://github.com/manopapad/proper">PropEr</a>. If you're also unable to use GPLed software
  there's <a href=https://github.com/krestenkrab/triq>triq</a>. I know very little about either.
</p>

<h2>Special case: OCaml</h2>

<p>
  OCaml seems to be suffering from a problem of being close enough to Haskell that people try to do a
  straight port of Quickcheck but far enough from Haskell that this doesn't work. The result is that
  there is <a href="https://github.com/alanfalloon/ocaml-quickcheck">a "mechanical port" of Quickcheck
  which is completely abandoned</a> and <a href="https://github.com/camlunity/ocaml-quickcheck">a fork
  of it that uses more idiomatic OCaml</a>. I'm insufficiently familiar with OCaml or its community
  to know if either is used or whether there is another one that is.
</p>

<h2>What does this have to do with Hypothesis?</h2>

<p>
  In some sense these are all "competitors" to Hypothesis, but we're perfectly happy not to compete.
</p>

<p>
  In the case of Erlang, I wouldn't even try. In the case of Scala, F#, or Clojure, I might at some
  point work with them to try to bring the best parts of Hypothesis to their existing implementation,
  but I don't consider them a priority - they're well served by what they have right now, and there
  are many languages that are not.
</p>

<p>
  For the rest though? I'm glad they exist! I care about testing about about high quality software,
  and they're doing their part to make it possible.
</p>

<p>
  But I feel they're being badly served by their underlying model, and that they feel quite unnatural
  to use in the context of a more conventional test setting. I think Hypothesis is the way forward,
  and I'll be doing my best <a href="/services/#ports-of-hypothesis-to-new-languages">to make it
  possible for everyone to use it in their language of choice</a>.
</p>
