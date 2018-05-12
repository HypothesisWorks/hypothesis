// "Bridging" root code that exists exclusively to provide
// a ruby -> Hypothesis engine binding. Long term the code
// in here is the only code that is going to stay in this
// crate, and everything else is going to get factored out
// into its own.

#![recursion_limit = "256"]
#![deny(warnings, missing_debug_implementations)]

extern crate core;
#[macro_use]
extern crate helix;
extern crate rand;

mod data;
mod distributions;
mod engine;
mod intminimize;

use std::mem;

use data::{DataSource, Status};
use distributions::Repeat;
use engine::Engine;

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

    def start_draw(&mut self){
      if let &mut Some(ref mut source) = &mut self.source {
        source.start_draw();
      }
    }

    def stop_draw(&mut self){
      if let &mut Some(ref mut source) = &mut self.source {
        source.stop_draw();
      }
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

  class HypothesisCoreBitPossible{
    struct {
      n_bits: u64,
    }

    def initialize(helix, n_bits: u64){
      return HypothesisCoreBitPossible{helix, n_bits: n_bits};
    }

    def provide(&mut self, data: &mut HypothesisCoreDataSource) -> Option<u64>{
      match &mut data.source {
        &mut None => None,
        &mut Some(ref mut source) => source.bits(self.n_bits).ok(),
      }
    }
  }

  class HypothesisCoreRepeatValues{
    struct {
      repeat: Repeat,
    }

    def initialize(helix, min_count: u64, max_count: u64, expected_count: f64){
      return HypothesisCoreRepeatValues{
        helix, repeat: Repeat::new(min_count, max_count, expected_count)
      }
    }

    def _should_continue(&mut self, data: &mut HypothesisCoreDataSource) -> Option<bool>{
      return data.source.as_mut().and_then(|ref mut source| {
        self.repeat.should_continue(source).ok()
      })
    }

    def reject(&mut self){
      self.repeat.reject();
    }
  }

  class HypothesisCoreIntegers{
    struct {
        bitlengths: distributions::Sampler,
    }
    def initialize(helix){
      return HypothesisCoreIntegers{helix,bitlengths: distributions::good_bitlengths()};
    }
    def provide(&mut self, data: &mut HypothesisCoreDataSource) -> Option<i64>{
      data.source.as_mut().and_then(|ref mut source| {
        distributions::integer_from_bitlengths(source, &self.bitlengths).ok()
      })
    }
  }

  class HypothesisCoreBoundedIntegers{
    struct {
        max_value: u64,
    }
    def initialize(helix, max_value: u64){
      return HypothesisCoreBoundedIntegers{helix, max_value: max_value};
    }

    def provide(&mut self, data: &mut HypothesisCoreDataSource) -> Option<u64>{
      data.source.as_mut().and_then(|ref mut source| {
        distributions::bounded_int(source, self.max_value).ok()
      })
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
