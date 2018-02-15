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
    MaxExamples,
    //MaxShrinks,
    Shutdown,
    //Error(String),
}

#[derive(Debug)]
enum LoopCommand {
    RunThis(DataSource),
    Finished(LoopExitReason, MainGenerationLoop),
}

#[derive(Debug)]
struct MainGenerationLoop {
    receiver: Receiver<TestResult>,
    sender: SyncSender<LoopCommand>,
    max_examples: u64,
    random: ChaChaRng,

    best_example: Option<TestResult>,

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
        let interesting_example = self.generate_examples()?;

        let mut shrinker = Shrinker::new(self, interesting_example, |r| {
            r.status == Status::Interesting
        });

        shrinker.run()?;

        return Err(LoopExitReason::Complete);
    }

    fn generate_examples(&mut self) -> Result<TestResult, LoopExitReason> {
        while self.valid_examples < self.max_examples
            && self.invalid_examples < 10 * self.max_examples
        {
            let r = self.random.gen();
            let result = self.execute(DataSource::from_random(r))?;
            if result.status == Status::Interesting {
                return Ok(result);
            }
        }
        return Err(LoopExitReason::MaxExamples);
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
                self.best_example = Some(result.clone());
                self.interesting_examples += 1;
            }
        }

        Ok(result)
    }
}

struct Shrinker<'owner, Predicate> {
    _predicate: Predicate,
    shrink_target: TestResult,
    changes: u64,
    main_loop: &'owner mut MainGenerationLoop,
}

impl<'owner, Predicate> Shrinker<'owner, Predicate>
where
    Predicate: Fn(&TestResult) -> bool,
{
    fn new(
        main_loop: &'owner mut MainGenerationLoop,
        shrink_target: TestResult,
        predicate: Predicate,
    ) -> Shrinker<'owner, Predicate> {
        assert!(predicate(&shrink_target));
        Shrinker {
            main_loop: main_loop,
            _predicate: predicate,
            shrink_target: shrink_target,
            changes: 0,
        }
    }

    fn predicate(&mut self, result: &TestResult) -> bool {
        let succeeded = (self._predicate)(result);
        if succeeded {
            self.changes += 1;
            self.shrink_target = result.clone();
        }
        succeeded
    }

    fn run(&mut self) -> StepResult {
        let mut prev = self.changes + 1;

        while prev != self.changes {
            prev = self.changes;
            self.binary_search_blocks()?;
            self.remove_intervals()?;
        }
        Ok(())
    }

    fn remove_intervals(&mut self) -> StepResult {
        // TODO: Actually track the data we need to make this
        // not quadratic.
        let mut i = 0;
        while i < self.shrink_target.record.len() {
            let start_length = self.shrink_target.record.len();

            let mut j = i + 1;
            while j < self.shrink_target.record.len() {
                assert!(j > i);
                let mut attempt = self.shrink_target.record.clone();
                attempt.drain(i..j);
                assert!(attempt.len() + (j - i) == self.shrink_target.record.len());
                let deleted = self.incorporate(&attempt)?;
                if !deleted {
                    j += 1;
                }
            }
            if start_length == self.shrink_target.record.len() {
                i += 1;
            }
        }
        Ok(())
    }

    fn binary_search_blocks(&mut self) -> StepResult {
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
        let result = self.main_loop.execute(DataSource::from_vec(buf.clone()))?;
        return Ok(self.predicate(&result));
    }
}

#[derive(Debug, Clone, Eq, PartialEq)]
enum EngineState {
    AwaitingCompletion,
    ReadyToProvide,
}

#[derive(Debug)]
pub struct Engine {
    // The next response from the main loop. Once
    // this is set to Some(Finished(_)) it stays that way,
    // otherwise it is cleared on access.
    loop_response: Option<LoopCommand>,

    state: EngineState,

    // Communication channels with the main testing loop
    handle: Option<thread::JoinHandle<()>>,
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

        let main_loop = MainGenerationLoop {
            max_examples: max_examples,
            random: ChaChaRng::from_seed(seed),
            sender: send_remote,
            receiver: recv_remote,
            best_example: None,
            valid_examples: 0,
            invalid_examples: 0,
            interesting_examples: 0,
        };

        let handle = thread::spawn(move || {
            main_loop.run();
        });

        Engine {
            loop_response: None,
            sender: send_local,
            receiver: recv_local,
            handle: Some(handle),
            state: EngineState::ReadyToProvide,
        }
    }

    pub fn mark_finished(&mut self, source: DataSource, status: Status) -> () {
        self.consume_test_result(source.to_result(status))
    }

    pub fn next_source(&mut self) -> Option<DataSource> {
        assert!(self.state == EngineState::ReadyToProvide);
        self.state = EngineState::AwaitingCompletion;

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
        match &self.loop_response {
            &Some(LoopCommand::Finished(
                _,
                MainGenerationLoop {
                    best_example: Some(ref result),
                    ..
                },
            )) => Some(DataSource::from_vec(result.record.clone())),
            _ => None,
        }
    }

    fn consume_test_result(&mut self, result: TestResult) -> () {
        assert!(self.state == EngineState::AwaitingCompletion);
        self.state = EngineState::ReadyToProvide;

        if self.has_shutdown() {
            return ();
        }

        // NB: Deliberately not matching on result. If this fails,
        // that's OK - it means the loop has shut down and when we ask
        // for data from it we'll get its shutdown response.
        let _ = self.sender.send(result);
    }

    pub fn was_unsatisfiable(&self) -> bool {
        match &self.loop_response {
            &Some(LoopCommand::Finished(_, ref main_loop)) => {
                main_loop.interesting_examples == 0 && main_loop.valid_examples == 0
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

    fn await_thread_termination(&mut self) {
        let mut maybe_handle = None;
        mem::swap(&mut self.handle, &mut maybe_handle);
        if let Some(handle) = maybe_handle {
            if let Err(boxed_msg) = handle.join() {
                // FIXME: This is awful but as far as I can tell this is
                // genuinely the only way to get the actual message out of the
                // panic in the child thread! It's boxed as an Any, and the
                // debug of Any just says "Any". Fortunately the main loop is
                // very much under our control so this doesn't matter too much
                // here, but yuck!
                if let Some(msg) = boxed_msg.downcast_ref::<&str>() {
                    panic!(msg.to_string());
                } else if let Some(msg) = boxed_msg.downcast_ref::<String>() {
                    panic!(msg.clone());
                } else {
                    panic!("BUG: Unexpected panic format in main loop");
                }
            }
        }
    }

    fn await_loop_response(&mut self) -> () {
        if self.loop_response.is_none() {
            match self.receiver.recv() {
                Ok(response) => {
                    self.loop_response = Some(response);
                    if self.has_shutdown() {
                        self.await_thread_termination();
                    }
                }
                Err(_) => {
                    self.await_thread_termination();
                    panic!("BUG: Unexpected silent termination of generation loop.")
                }
            }
        }
    }
}
