# README #

This is the main hypothesis.works site. It is originally based off the [rifyll](https://github.com/itsrifat/rifyll) Jekyll template.

## Getting started

You need Git, make and Docker installed.

To run a local copy of the site:

```console
$ git clone git@github.com:HypothesisWorks/HypothesisWorks.github.io.git
$ make serve
```

The site should be running on <http://localhost:5858>.
If you make changes to the source files, it will automatically update.

To build a one-off set of static HTML files:

```console
$ make build
```

When you push to master, the site is automatically built and served by GitHub Pages.
