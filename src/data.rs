// Module representing core data types that Hypothesis
// needs.

use rand::{ChaChaRng, Rng};

pub type DataStream = Vec<u64>;

#[derive(Debug, Clone)]
enum BitGenerator {
    Random(ChaChaRng),
    Recorded(DataStream),
}

// Main entry point for running a test:
// A test function takes a DataSource, uses it to
// produce some data, and the DataSource records the
// relevant information about what they did.
#[derive(Debug, Clone)]
pub struct DataSource {
    bitgenerator: BitGenerator,
    record: DataStream,
}

impl DataSource {
    pub fn bits(&mut self, n_bits: u64) -> Option<u64> {
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
            record: DataStream::new(),
        };
    }

    pub fn from_random(random: ChaChaRng) -> DataSource {
        return DataSource::new(BitGenerator::Random(random));
    }

    pub fn from_vec(record: DataStream) -> DataSource {
        return DataSource::new(BitGenerator::Recorded(record));
    }

    pub fn to_result(self, status: Status) -> TestResult {
        TestResult {
            record: self.record,
            status: status,
        }
    }
}

// Status indicates the result that we got from completing
// a single test execution.
#[derive(Debug, Clone, Eq, PartialEq)]
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
    Interesting,
}

// Once a data source is finished it "decays" to a
// TestResult, that retains a trace of all the information
// we needed from the DataSource. It is these we keep around,
// not the original DataSource objects.
#[derive(Debug, Clone)]
pub struct TestResult {
    pub record: DataStream,
    pub status: Status,
}

impl TestResult {
    pub fn dummy() -> TestResult {
        TestResult {
            record: Vec::new(),
            status: Status::Invalid,
        }
    }
}
