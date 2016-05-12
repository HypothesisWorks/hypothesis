---
layout: post
tags: technical python details
date: 2016-05-11 10:00
title: Generating the right data
published: true
---

One thing that often causes people problems is figuring out how to generate the right data to fit their data
model. You can start with just generating strings and integers, but eventually you want to be able to generate
objects from your domain model. Hypothesis provides a lot of tools to help you build data as you want it,
but sometimes the choice can be a bit overwhelming.

Here's a worked example to walk you through some of the details and help you get to grips with how to use
them.

<!--more-->

Suppose we have the following class:

```python

class Project(object):
    def __init__(self, name, start, end):
        self.start = start
        self.name = name
        self.end = end
```

A project has a name, a start date, and an end date.

So how do we generate such a thing?

```pycon

```
