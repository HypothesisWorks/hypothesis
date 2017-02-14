#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>

#define mt_PARAM_N 312

struct mt {
    uint64_t mt[mt_PARAM_N]; /* the array for the state vector  */
    int16_t mti;
};

typedef struct {
  size_t n_items;
  size_t item_mask;
  size_t *alias_table;
  double *probabilities;

  struct mt mersenne_twister;
} random_sampler;


static void mt_seed(struct mt *mt, uint64_t seed);
static uint64_t genrand64_int64(struct mt *r);


random_sampler *random_sampler_new(size_t n_items, double *weights, uint64_t seed){
  void *data = malloc(sizeof(random_sampler) + n_items * sizeof(size_t) + n_items * sizeof(double));

  random_sampler *result = (random_sampler*)data;
    result->n_items = n_items;

  mt_seed(&(result->mersenne_twister), seed);


  size_t mask = n_items;
  mask |= (mask >> 1);
  mask |= (mask >> 2);
  mask |= (mask >> 4);
  mask |= (mask >> 8);
  mask |= (mask >> 16);
  mask |= (mask >> 32);
  result->item_mask = mask;

  result->alias_table = (size_t*)(data + sizeof(random_sampler));
  result->probabilities =  (double*)(data + sizeof(random_sampler) + n_items * sizeof(size_t));

  double min = INFINITY;
  double max = -INFINITY;
  double total = 0.0;

  for(size_t i = 0; i < n_items; i++){
    double x = weights[i];
    if(x < min) min = x;
    if(x > max) max = x;
    total += x;
  }
  if((min == max) || (total <= 0) || isnan(total)){
    // fast path for a uniform sampler
    
    for(size_t i = 0; i < n_items; i++){
      result->alias_table[i] = i;
      result->probabilities[i] = 1.0;
    }
  } else {
    assert(n_items > 1);

    size_t *small = malloc(sizeof(size_t) * n_items);
    size_t *large = malloc(sizeof(size_t) * n_items);

    for(size_t i = 0; i < n_items; i++){
      result->probabilities[i] = weights[i] * n_items / total;
    }

    size_t small_height = 0;
    size_t large_height = 0;

    for(size_t i = 0; i < n_items; i++){
      double p = weights[i] * n_items / total;
      result->probabilities[i] = p;
      if(p < 1){
        small[small_height++] = i;
      } else {
        large[large_height++] = i;
      }
    }

    while((small_height > 0) && (large_height > 0)){
      size_t l = small[--small_height];
      size_t g = large[--large_height];
      assert(result->probabilities[g] >= 1);
      assert(result->probabilities[l] <= 1);
      result->alias_table[l] = g;
      result->probabilities[g] = (result->probabilities[l] + result->probabilities[g]) - 1;
      if(result->probabilities[g] < 1){
        small[small_height++] = g;
      } else {
        large[large_height++] = g;
      }
    }

    while(large_height > 0){
      size_t i = large[--large_height];
      result->alias_table[i] = i;
      result->probabilities[i] = 1.0;
    }
    while(small_height > 0){
      size_t i = small[--small_height];
      result->alias_table[i] = i;
      result->probabilities[i] = 1.0;
    }

    free(small);
    free(large);
  }
  return result;
}

void random_sampler_free(random_sampler *sampler){
  free(sampler);
}

void random_sampler_debug(random_sampler *sampler){
    printf("random_sampler for %d items\n", (int)(sampler->n_items));
    printf("Aliases: ");
    for(size_t i = 0; i < sampler->n_items; i++)
        printf("%d ", (int)(sampler->alias_table[i]));
    printf("\nWeights: ");
    for(size_t i = 0; i < sampler->n_items; i++)
        printf("%.2f ", (sampler->probabilities[i]));
    printf("\n  ");
}

static double mt_random_double(struct mt *mt);

size_t random_sampler_sample(random_sampler *sampler){
  struct mt *mt = &(sampler->mersenne_twister);
  size_t i = sampler->n_items;;
  while(i >= sampler->n_items){
    // FIXME: Potentially wasting a lot of bits here.
    i = genrand64_int64(mt) & sampler->item_mask;
  }
  size_t j = sampler->alias_table[i];
  if(i == j) return i;
  if(mt_random_double(mt) <= sampler->probabilities[i]){
    return i;
  } else {
    return j;
  }
}

/* 
   A C-program for MT19937-64 (2004/9/29 version).
   Coded by Takuji Nishimura and Makoto Matsumoto.

   This is a 64-bit version of Mersenne Twister pseudorandom number
   generator.

   Before using, initialize the state by using init_genrand64(seed)  
   or init_by_array64(init_key, key_length).

   Copyright (C) 2004, Makoto Matsumoto and Takuji Nishimura,
   All rights reserved.                          

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:

     1. Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.

     2. Redistributions in binary form must reproduce the above copyright
        notice, this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.

     3. The names of its contributors may not be used to endorse or promote 
        products derived from this software without specific prior written 
        permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
   A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
   PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
   LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
   NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

   References:
   T. Nishimura, ``Tables of 64-bit Mersenne Twisters''
     ACM Transactions on Modeling and 
     Computer Simulation 10. (2000) 348--357.
   M. Matsumoto and T. Nishimura,
     ``Mersenne Twister: a 623-dimensionally equidistributed
       uniform pseudorandom number generator''
     ACM Transactions on Modeling and 
     Computer Simulation 8. (Jan. 1998) 3--30.

   Any feedback is very welcome.
   http://www.math.hiroshima-u.ac.jp/~m-mat/MT/emt.html
   email: m-mat @ math.sci.hiroshima-u.ac.jp (remove spaces)
*/

/* The code has been modified to store internal state in heap/stack
 * allocated memory, rather than statically allocated memory, to allow
 * multiple instances running in the same address space. */

#define NN mt_PARAM_N
#define MM 156
#define MATRIX_A 0xB5026F5AA96619E9ULL
#define UM 0xFFFFFFFF80000000ULL /* Most significant 33 bits */
#define LM 0x7FFFFFFFULL /* Least significant 31 bits */

static uint64_t genrand64_int64(struct mt *r);

/* initializes mt[NN] with a seed */
static void mt_seed(struct mt *mt, uint64_t seed)
{
    mt->mt[0] = seed;
    uint16_t mti = 0;
    for (mti=1; mti<NN; mti++) {
        mt->mt[mti] = (6364136223846793005ULL *
            (mt->mt[mti-1] ^ (mt->mt[mti-1] >> 62)) + mti);
    }
    mt->mti = mti;
}

/* Generate a random number on [0,1]-real-interval. */
static double mt_random_double(struct mt *mt)
{
    return (genrand64_int64(mt) >> 11) * (1.0/9007199254740991.0);
}

/* generates a random number on [0, 2^64-1]-interval */
static uint64_t genrand64_int64(struct mt *r)
{
    int i;
    uint64_t x;
    static uint64_t mag01[2]={0ULL, MATRIX_A};

    if (r->mti >= NN) { /* generate NN words at one time */

        /* if init has not been called, */
        /* a default initial seed is used */
        if (r->mti == NN+1)
            mt_seed(r, 5489ULL);

        for (i=0;i<NN-MM;i++) {
            x = (r->mt[i]&UM)|(r->mt[i+1]&LM);
            r->mt[i] = r->mt[i+MM] ^ (x>>1) ^ mag01[(int)(x&1ULL)];
        }
        for (;i<NN-1;i++) {
            x = (r->mt[i]&UM)|(r->mt[i+1]&LM);
            r->mt[i] = r->mt[i+(MM-NN)] ^ (x>>1) ^ mag01[(int)(x&1ULL)];
        }
        x = (r->mt[NN-1]&UM)|(r->mt[0]&LM);
        r->mt[NN-1] = r->mt[MM-1] ^ (x>>1) ^ mag01[(int)(x&1ULL)];

        r->mti = 0;
    }
  
    x = r->mt[r->mti++];

    x ^= (x >> 29) & 0x5555555555555555ULL;
    x ^= (x << 17) & 0x71D67FFFEDA60000ULL;
    x ^= (x << 37) & 0xFFF7EEE000000000ULL;
    x ^= (x >> 43);

    return x;
}
