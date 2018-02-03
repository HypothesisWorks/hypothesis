// Core module that provides a main execution loop and
// the API that can be used to get test data from it.

use rand::{ChaChaRng, Rng, SeedableRng};

use std::sync::mpsc::{sync_channel, Receiver, SyncSender};
use std::thread;
use std::mem;

use data::{DataSource, DataStream, Status, TestResult};

#[derive(Debug, Clone)]
enum LoopExitReason {
    Complete,
    //MaxExamples,
    //MaxShrinks,
    Shutdown,
    //Error(String),
}

#[derive(Debug)]
enum LoopCommand {
    RunThis(DataSource),
    Finished(LoopExitReason, MainGenerationLoop),
    UnexpectedTermination,
}

#[derive(Debug)]
struct MainGenerationLoop {
    receiver: Receiver<TestResult>,
    sender: SyncSender<LoopCommand>,
    max_examples: u64,
    random: ChaChaRng,

    shrink_target: TestResult,

    valid_examples: u64,
    invalid_examples: u64,
    interesting_examples: u64,
}

type StepResult = Result<(), LoopExitReason>;

impl MainGenerationLoop {
    fn run(mut self) {
        let result = self.loop_body();
        match result {
            // Silent shutdown when the main thread terminates
            Err(LoopExitReason::Shutdown) => (),
            Err(reason) => {
                // Must clone because otherwise it is borrowed.
                let shutdown_sender = self.sender.clone();
                shutdown_sender
                    .send(LoopCommand::Finished(reason, self))
                    .unwrap()
            }
            Ok(_) => panic!("BUG: Generation loop was not supposed to return normally."),
        }
    }

    fn loop_body(&mut self) -> StepResult {
        self.generate_examples()?;
        self.shrink_examples()?;
        return Err(LoopExitReason::Complete);
    }

    fn generate_examples(&mut self) -> StepResult {
        while self.valid_examples < self.max_examples
            && self.shrink_target.status != Status::Interesting
        {
            let r = self.random.gen();
            self.execute(DataSource::from_random(r))?;
        }
        return Ok(());
    }

    fn shrink_examples(&mut self) -> StepResult {
        assert!(self.shrink_target.status == Status::Interesting);
        let mut i = 0;

        let mut attempt = self.shrink_target.record.clone();

        while i < self.shrink_target.record.len() {
            assert!(attempt.len() >= self.shrink_target.record.len());
            attempt.truncate(self.shrink_target.record.len());

            let mut hi = self.shrink_target.record[i];

            if hi > 0 {
                attempt[i] = 0;
                let zeroed = self.incorporate(&attempt)?;
                if !zeroed {
                    let mut lo = 0;
                    // Binary search to find the smallest value we can
                    // replace this with.
                    while lo + 1 < hi {
                        let mid = lo + (hi - lo) / 2;
                        attempt[i] = mid;
                        let succeeded = self.incorporate(&attempt)?;
                        if succeeded {
                            hi = mid;
                        } else {
                            lo = mid;
                        }
                    }
                    attempt[i] = hi;
                }
            }

            i += 1;
        }

        Ok(())
    }

    fn incorporate(&mut self, buf: &DataStream) -> Result<bool, LoopExitReason> {
        let result = self.execute(DataSource::from_vec(buf.clone()))?;
        return Ok(result.status == Status::Interesting);
    }

    fn execute(&mut self, source: DataSource) -> Result<TestResult, LoopExitReason> {
        let result = match self.sender.send(LoopCommand::RunThis(source)) {
            Ok(_) => match self.receiver.recv() {
                Ok(t) => t,
                Err(_) => return Err(LoopExitReason::Shutdown),
            },
            Err(_) => return Err(LoopExitReason::Shutdown),
        };
        match result.status {
            Status::Overflow => (),
            Status::Invalid => self.invalid_examples += 1,
            Status::Valid => self.valid_examples += 1,
            Status::Interesting => {
                self.shrink_target = result.clone();
                self.interesting_examples += 1;
            }
        }

        Ok(result)
    }
}

#[derive(Debug)]
pub struct Engine {
    // Information that we might be asked for.
    best_example: Option<TestResult>,

    // The next response from the main loop. Once
    // this is set to Some(Finished(_)) it stays that way,
    // otherwise it is cleared on access.
    loop_response: Option<LoopCommand>,

    // Communication channels with the main testing loop
    receiver: Receiver<LoopCommand>,
    sender: SyncSender<TestResult>,
}

impl Clone for Engine {
    fn clone(&self) -> Engine {
        panic!("BUG: The Engine was unexpectedly cloned");
    }
}

impl Engine {
    pub fn new(max_examples: u64, seed: &[u32]) -> Engine {
        let (send_local, recv_remote) = sync_channel(1);
        let (send_remote, recv_local) = sync_channel(1);

        let engine = Engine {
            best_example: None,
            loop_response: None,
            sender: send_local,
            receiver: recv_local,
        };

        let main_loop = MainGenerationLoop {
            max_examples: max_examples,
            random: ChaChaRng::from_seed(seed),
            sender: send_remote,
            receiver: recv_remote,

            shrink_target: TestResult::dummy(),
            valid_examples: 0,
            invalid_examples: 0,
            interesting_examples: 0,
        };

        thread::spawn(move || {
            main_loop.run();
        });

        return engine;
    }

    pub fn mark_finished(&mut self, source: DataSource, status: Status) -> () {
        self.consume_test_result(source.to_result(status))
    }

    pub fn next_source(&mut self) -> Option<DataSource> {
        self.await_loop_response();

        let mut local_result = None;
        mem::swap(&mut local_result, &mut self.loop_response);

        match local_result {
            Some(LoopCommand::RunThis(source)) => return Some(source),
            None => panic!("BUG: Loop response should not be empty at this point"),
            _ => {
                self.loop_response = local_result;
                return None;
            }
        }
    }

    pub fn best_source(&self) -> Option<DataSource> {
        match &self.best_example {
            &Some(ref result) => Some(DataSource::from_vec(result.record.clone())),
            _ => None,
        }
    }

    fn consume_test_result(&mut self, result: TestResult) -> () {
        match result.status {
            Status::Interesting => self.best_example = Some(result.clone()),
            _ => (),
        };

        if self.has_shutdown() {
            return ();
        }

        match self.sender.send(result) {
            Ok(_) => (),
            Err(_) => self.loop_went_oops(),
        }
    }

    fn loop_went_oops(&mut self) {
        self.loop_response = Some(LoopCommand::UnexpectedTermination)
    }

    pub fn was_unsatisfiable(&self) -> bool {
        match &self.loop_response {
            &Some(LoopCommand::Finished(_, ref main_loop)) => {
                main_loop.interesting_examples > 0 || main_loop.valid_examples > 0
            }
            _ => false,
        }
    }

    fn has_shutdown(&mut self) -> bool {
        match &self.loop_response {
            &Some(LoopCommand::Finished(..)) => true,
            _ => false,
        }
    }

    fn await_loop_response(&mut self) -> () {
        if self.loop_response.is_none() {
            match self.receiver.recv() {
                Ok(response) => self.loop_response = Some(response),
                Err(_) => self.loop_went_oops(),
            }
        }
    }
}
