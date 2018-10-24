// "Bridging" root code that exists exclusively to provide
// a ruby -> Hypothesis engine binding.

#![recursion_limit = "256"]
#![deny(warnings, missing_debug_implementations)]

extern crate core;
#[macro_use]
extern crate helix;
extern crate rand;
extern crate conjecture;

use std::mem;

use conjecture::data::{DataSource, Status, TestResult};
use conjecture::distributions::Repeat;
use conjecture::distributions;
use conjecture::engine::Engine;
use conjecture::database::{BoxedDatabase, NoDatabase, DirectoryDatabase};

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
      interesting_examples: Vec<TestResult>,
    }

    def initialize(helix, name: String, database_path: Option<String>, seed: u64, max_examples: u64){
      let xs: [u32; 2] = [seed as u32, (seed >> 32) as u32];
      let db: BoxedDatabase = match database_path {
        None => Box::new(NoDatabase),
        Some(path) => Box::new(DirectoryDatabase::new(path)),
      };

      HypothesisCoreEngine{
        helix,
        engine: Engine::new(name, max_examples, &xs, db),
        pending: None,
        interesting_examples: Vec::new(),
      }
    }

    def new_source(&mut self) -> Option<HypothesisCoreDataSource> {
      match self.engine.next_source() {
        None => {
          self.interesting_examples = self.engine.list_minimized_examples();
          None
        },
        Some(source) => {
          self.pending = Some(source);
          Some(HypothesisCoreDataSource::new(self))
        },
      }
    }

    def count_failing_examples(&self) -> usize {
      self.interesting_examples.len()
    }

    def failing_example(&mut self, i: usize) -> HypothesisCoreDataSource {
      self.pending = Some(
        DataSource::from_vec(self.interesting_examples[i].record.clone())
      );
      HypothesisCoreDataSource::new(self)
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

    def finish_interesting(&mut self, child: &mut HypothesisCoreDataSource, label: u64){
      mark_child_status(&mut self.engine, child, Status::Interesting(label));
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
