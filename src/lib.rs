// "Bridging" root code that exists exclusively to provide
// a ruby -> Hypothesis engine binding. Long term the code
// in here is the only code that is going to stay in this
// crate, and everything else is going to get factored out
// into its own.

#![recursion_limit = "128"]
#![deny(warnings, missing_debug_implementations)]

#[macro_use]
extern crate helix;
extern crate rand;

mod engine;
mod data;

use std::mem;

use engine::Engine;
use data::{DataSource, Status};

ruby! {
  class HypothesisCoreDataSource {
    struct {
      source: Option<DataSource>,
    }

    def initialize(helix, engine: &mut HypothesisCoreEngine){
      let mut result = HypothesisCoreDataSource{helix, source: None};
      mem::swap(&mut result.source, &mut engine.pending);
      return result;
    }
  }

  class HypothesisCoreEngine {
    struct {
      engine: Engine,
      pending: Option<DataSource>,
    }

    def initialize(helix, seed: u64, max_examples: u64){
      let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
      HypothesisCoreEngine{
        helix,
        engine: Engine::new(max_examples, &xs),
        pending: None,
      }
    }

    def new_source(&mut self) -> Option<HypothesisCoreDataSource> {
      match self.engine.next_source() {
        None => None,
        Some(source) => {
          self.pending = Some(source);
          Some(HypothesisCoreDataSource::new(self))
        },
      }
    }

    def failing_example(&mut self) -> Option<HypothesisCoreDataSource> {
      if let Some(source) = self.engine.best_source() {
        self.pending = Some(source);
        return Some(HypothesisCoreDataSource::new(self));
      } else {
        return None;
      }
    }

    def was_unsatisfiable(&mut self) -> bool {
      self.engine.was_unsatisfiable()
    }

    def finish_overflow(&mut self, child: &mut HypothesisCoreDataSource){
      mark_child_status(&mut self.engine, child, Status::Overflow);
    }

    def finish_invalid(&mut self, child: &mut HypothesisCoreDataSource){
      mark_child_status(&mut self.engine, child, Status::Invalid);
    }

    def finish_interesting(&mut self, child: &mut HypothesisCoreDataSource){
      mark_child_status(&mut self.engine, child, Status::Interesting);
    }

    def finish_valid(&mut self, child: &mut HypothesisCoreDataSource){
      mark_child_status(&mut self.engine, child, Status::Valid);
    }
  }

  class HypothesisCoreBitProvider{
    struct {
      n_bits: u64,
    }

    def initialize(helix, n_bits: u64){
      return HypothesisCoreBitProvider{helix, n_bits: n_bits};
    }

    def provide(&mut self, data: &mut HypothesisCoreDataSource) -> Option<u64>{
      match &mut data.source {
        &mut None => None,
        &mut Some(ref mut source) => source.bits(self.n_bits).ok(),
      }
    }
  }
}

fn mark_child_status(engine: &mut Engine, child: &mut HypothesisCoreDataSource, status: Status) {
    let mut replacement = None;
    mem::swap(&mut replacement, &mut child.source);

    match replacement {
        Some(source) => engine.mark_finished(source, status),
        None => (),
    }
}
