#![deny(warnings, missing_debug_implementations, missing_copy_implementations)]

#[macro_use]
extern crate helix;
extern crate rand;

use rand::{ChaChaRng, Rng, SeedableRng};
use std::collections::HashMap;

#[derive(Debug, Clone)]
struct DataSource {
    random: ChaChaRng,
}

ruby! {
  class HypothesisCoreEngine {
    struct {
      random: ChaChaRng,
      next_id: u64,
      children: HashMap<u64, DataSource>,
    }

    def initialize(helix, seed: u64){
      let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
      HypothesisCoreEngine{
        helix,
        random: ChaChaRng::from_seed(&xs),
        next_id: 0,
        children: HashMap::new(),
      }
    }

    def new_source(&mut self) -> u64 {
      let result = self.next_id;
      self.children.insert(result, DataSource{random: self.random.clone()});
      self.random.next_u64();
      self.next_id += 1;
      return result;
    }

    def bits(&mut self, id: u64, n_bits: u64) -> Option<u64> {
      match self.children.get_mut(&id) {
        None => return None,
        Some(source) => {
          let n: u64 = source.random.next_u64();
          if n_bits >= 64 {
            return Some(n);
          } else {
            let mask = (1 << n_bits) - 1;
            let r: u64 = n & mask;
            return Some(r);
          }
        }
      }
    }
  }
}
