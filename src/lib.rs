// "Bridging" root code that exists exclusively to provide
// a ruby -> Hypothesis engine binding. Long term the code
// in here is the only code that is going to stay in this
// crate, and everything else is going to get factored out
// into its own.

#![recursion_limit = "128"]
#![deny(warnings, missing_debug_implementations, missing_copy_implementations)]

#[macro_use]
extern crate helix;
extern crate rand;

mod engine;
mod data;

use std::collections::HashMap;
use engine::Engine;
use data::{DataSource, Status};

ruby! {
  class HypothesisCoreEngine {
    struct {
      next_id: u64,
      children: HashMap<u64, DataSource>,
      engine: Engine,
    }

    def initialize(helix, seed: u64, max_examples: u64){
      let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
      HypothesisCoreEngine{
        helix,
        next_id: 0,
        children: HashMap::new(),
        engine: Engine::new(max_examples, &xs),
      }
    }

    def new_source(&mut self) -> Option<u64> {
      match self.engine.next_source() {
        None => None,
        Some(source) => {
          let result = self.next_id;
          self.children.insert(result, source);
          self.next_id += 1;
          Some(result)
        }
      }
    }

    def failing_example(&mut self) -> Option<u64> {
      if let Some(source) = self.engine.best_source() {
        let result = self.next_id;
        self.children.insert(result, source);
        self.next_id += 1;
        return Some(result);
      } else {
        return None;
      }
    }

    def was_unsatisfiable(&mut self) -> bool {
      self.engine.was_unsatisfiable()
    }

    def finish_overflow(&mut self, id: u64){
      mark_status_id(&mut self.engine, &mut self.children, id, Status::Overflow);
    }

    def finish_invalid(&mut self, id: u64){
      mark_status_id(&mut self.engine, &mut self.children, id, Status::Invalid);
    }

    def finish_interesting(&mut self, id: u64){
      mark_status_id(&mut self.engine, &mut self.children, id, Status::Interesting);
    }

    def finish_valid(&mut self, id: u64){
      mark_status_id(&mut self.engine, &mut self.children, id, Status::Valid);
    }

    def bits(&mut self, id: u64, n_bits: u64) -> Option<u64> {
      match self.children.get_mut(&id) {
        None => return None,
        Some(source) => return source.bits(n_bits)
      }
    }
  }
}

fn mark_status_id(
    engine: &mut Engine,
    children: &mut HashMap<u64, DataSource>,
    id: u64,
    status: Status,
) {
    match children.remove(&id) {
        Some(source) => engine.mark_finished(source, status),
        None => (),
    }
}
