// Module representing core data types that Hypothesis
// needs.

use rand::{ChaChaRng, Rng};
use std::cmp::Ordering;
use std::collections::HashSet;

pub type DataStream = Vec<u64>;
pub type DataStreamSlice = [u64];

#[derive(Debug, Clone)]
pub struct FailedDraw;

#[derive(Debug, Clone)]
enum BitGenerator {
    Random(ChaChaRng),
    Recorded(DataStream),
}

// Records information corresponding to a single draw call.
#[derive(Debug, Clone)]
pub struct DrawInProgress {
    depth: usize,
    start: usize,
    end: Option<usize>,
}

// Records information corresponding to a single draw call.
#[derive(Debug, Clone)]
pub struct Draw {
    pub depth: usize,
    pub start: usize,
    pub end: usize,
}

// Main entry point for running a test:
// A test function takes a DataSource, uses it to
// produce some data, and the DataSource records the
// relevant information about what they did.
#[derive(Debug, Clone)]
pub struct DataSource {
    bitgenerator: BitGenerator,
    record: DataStream,
    sizes: Vec<u64>,
    draws: Vec<DrawInProgress>,
    draw_stack: Vec<usize>,
    written_indices: HashSet<usize>,
}

impl DataSource {
    fn new(generator: BitGenerator) -> DataSource {
        DataSource {
            bitgenerator: generator,
            record: DataStream::new(),
            sizes: Vec::new(),
            draws: Vec::new(),
            draw_stack: Vec::new(),
            written_indices: HashSet::new(),
        }
    }

    pub fn from_random(random: ChaChaRng) -> DataSource {
        DataSource::new(BitGenerator::Random(random))
    }

    pub fn from_vec(record: DataStream) -> DataSource {
        DataSource::new(BitGenerator::Recorded(record))
    }

    pub fn start_draw(&mut self) {
        let i = self.draws.len();
        let depth = self.draw_stack.len();
        let start = self.record.len();

        self.draw_stack.push(i);
        self.draws.push(DrawInProgress {
            start,
            end: None,
            depth,
        });
    }

    pub fn stop_draw(&mut self) {
        assert!(!self.draws.is_empty());
        assert!(!self.draw_stack.is_empty());
        let i = self.draw_stack.pop().unwrap();
        let end = self.record.len();
        self.draws[i].end = Some(end);
    }

    pub fn write(&mut self, value: u64) -> Result<(), FailedDraw> {
        match self.bitgenerator {
            BitGenerator::Recorded(ref mut v) if self.record.len() >= v.len() => Err(FailedDraw),
            _ => {
                self.sizes.push(0);
                self.record.push(value);
                Ok(())
            }
        }
    }

    pub fn bits(&mut self, n_bits: u64) -> Result<u64, FailedDraw> {
        self.sizes.push(n_bits);
        let mut result = match self.bitgenerator {
            BitGenerator::Random(ref mut random) => random.next_u64(),
            BitGenerator::Recorded(ref mut v) => {
                if self.record.len() >= v.len() {
                    return Err(FailedDraw);
                } else {
                    v[self.record.len()]
                }
            }
        };

        if n_bits < 64 {
            let mask = (1 << n_bits) - 1;
            result &= mask;
        };

        self.record.push(result);

        Ok(result)
    }

    pub fn into_result(self, status: Status) -> TestResult {
        TestResult {
            record: self.record,
            status,
            written_indices: self.written_indices,
            sizes: self.sizes,
            draws: self
                .draws
                .into_iter()
                .filter_map(|d| match d {
                    DrawInProgress {
                        depth,
                        start,
                        end: Some(end),
                    } if start < end => Some(Draw { start, end, depth }),
                    DrawInProgress { end: None, .. } => {
                        assert!(status == Status::Invalid || status == Status::Overflow);
                        None
                    }
                    _ => None,
                })
                .collect(),
        }
    }
}

// Status indicates the result that we got from completing
// a single test execution.
#[derive(Debug, Clone, Eq, PartialEq, Copy)]
pub enum Status {
    // The test tried to read more data than we had for it.
    Overflow,

    // Some important precondition of the test was not
    // satisfied.
    Invalid,

    // This test ran successfully to completion without
    // anything of note happening.
    Valid,

    // This was an interesting test execution! (Usually this
    // means failing, but for things like find it may not).
    Interesting(u64),
}

// Once a data source is finished it "decays" to a
// TestResult, that retains a trace of all the information
// we needed from the DataSource. It is these we keep around,
// not the original DataSource objects.
#[derive(Debug, Clone)]
pub struct TestResult {
    pub record: DataStream,
    pub status: Status,
    pub draws: Vec<Draw>,
    pub sizes: Vec<u64>,
    pub written_indices: HashSet<usize>,
}

impl Ord for TestResult {
    fn cmp(&self, other: &TestResult) -> Ordering {
        self.record
            .len()
            .cmp(&other.record.len())
            .then(self.record.cmp(&other.record))
    }
}

impl PartialOrd for TestResult {
    fn partial_cmp(&self, other: &TestResult) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for TestResult {
    fn eq(&self, other: &TestResult) -> bool {
        self.record == other.record
    }
}

impl Eq for TestResult {}
