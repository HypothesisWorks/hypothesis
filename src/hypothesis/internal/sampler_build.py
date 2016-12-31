# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os

import cffi

ffibuilder = cffi.FFI()

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

assert os.path.basename(SRC) == 'src', SRC

with open(
    os.path.join(os.path.dirname(__file__), 'sampler.c'),
) as i:
    ffibuilder.set_source(
        'hypothesis.internal._sampler', i.read()

    )

ffibuilder.cdef("""
    void *random_sampler_new(size_t n_items, double *weights);
    void random_sampler_free(void *data);
    size_t random_sampler_sample(void *data, void* mt);
    void random_sampler_debug(void *data);

    void *mersenne_twister_new(uint64_t seed);
    void mersenne_twister_free(void *mt);

    void *sampler_family_new(size_t capacity, uint64_t seed);
    void sampler_family_free(void *samplers);
    size_t sampler_family_sample(
        void *samplers, size_t n_items, double *weights);
""")

# Putting this at the module level is gross, but AFAICT it's the only way to
# get custom CFLAGS working with cffi_modules out of the box without doing a
# bunch of extra work.
os.environ['CFLAGS'] = '--std=c99'

if __name__ == '__main__':
    os.chdir(SRC)
    ffibuilder.compile(verbose=True)
