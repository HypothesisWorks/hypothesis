#![deny(warnings, missing_debug_implementations, missing_copy_implementations)]

#[macro_use]
extern crate helix;
extern crate rand;

use rand::{ChaChaRng, Rng, SeedableRng};
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Debug, Clone)]
enum BitGenerator {
    Random(ChaChaRng),
    Recorded(Rc<Vec<u64>>),
}

#[derive(Debug, Clone)]
struct DataSource {
    bitgenerator: BitGenerator,
    record: Vec<u64>,
}

#[derive(Debug, Clone)]
enum Status {
    Invalid,
    Valid,
    Interesting,
}

#[derive(Debug, Clone)]
struct Engine {
    random: ChaChaRng,
    max_examples: u64,
    valid_examples: u64,
    invalid_examples: u64,
    interesting_examples: u64,
    best_example: Option<Rc<Vec<u64>>>,
}

impl DataSource {
    fn bits(&mut self, n_bits: u64) -> Option<u64> {
        let mut result = match self.bitgenerator {
            BitGenerator::Random(ref mut random) => random.next_u64(),
            BitGenerator::Recorded(ref mut v) => if self.record.len() >= v.len() {
                return None;
            } else {
                v[self.record.len()]
            },
        };

        if n_bits < 64 {
            let mask = (1 << n_bits) - 1;
            result &= mask;
        };

        self.record.push(result);

        return Some(result);
    }

    fn new(generator: BitGenerator) -> DataSource {
        return DataSource {
            bitgenerator: generator,
            record: Vec::new(),
        };
    }

    fn from_random(random: ChaChaRng) -> DataSource {
        return DataSource::new(BitGenerator::Random(random));
    }

    fn from_vec(record: Rc<Vec<u64>>) -> DataSource {
        return DataSource::new(BitGenerator::Recorded(record));
    }
}

impl Engine {
    fn new(max_examples: u64, seed: &[u32]) -> Engine {
        return Engine {
            random: ChaChaRng::from_seed(seed),
            max_examples: max_examples,
            valid_examples: 0,
            invalid_examples: 0,
            interesting_examples: 0,
            best_example: None,
        };
    }

    fn should_continue(&self) -> bool {
        return (self.valid_examples < self.max_examples)
            && (self.valid_examples + self.invalid_examples < self.max_examples * 10)
            && (self.interesting_examples == 0);
    }

    fn mark_finished(&mut self, source: DataSource, status: Status) {
        match status {
            Status::Valid => self.valid_examples += 1,
            Status::Invalid => self.invalid_examples += 1,
            Status::Interesting => {
                self.interesting_examples += 1;
                self.best_example = Some(Rc::new(source.record));
            }
        }
    }

    fn new_source(&mut self) -> DataSource {
        return DataSource::from_random(self.random.gen());
    }

    fn failing_example(&self) -> Option<DataSource> {
        match self.best_example {
            None => return None,
            Some(ref v) => return Some(DataSource::from_vec(v.clone())),
        }
    }
}

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

    def was_unsatisfiable(&self) -> bool {
      return self.engine.valid_examples == 0 && self.engine.interesting_examples == 0;
    }

    def new_source(&mut self) -> u64 {
      let result = self.next_id;
      self.children.insert(result, self.engine.new_source());
      self.next_id += 1;
      return result;
    }

    def failing_example(&mut self) -> Option<u64> {
      if let Some(source) = self.engine.failing_example() {
        let result = self.next_id;
        self.children.insert(result, source);
        self.next_id += 1;
        return Some(result);
      } else {
        return None;
      }
    }

    def should_continue(&self) -> bool {
      return self.engine.should_continue();
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
