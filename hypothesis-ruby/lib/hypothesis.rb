# frozen_string_literal: true

require_relative 'hypothesis/junkdrawer'
require_relative 'hypothesis/errors'
require_relative 'hypothesis/possible'
require_relative 'hypothesis/testcase'
require_relative 'hypothesis/engine'
require_relative 'hypothesis/world'

# This is the main module for using Hypothesis.
# It is expected that you will include this in your
# tests, but its methods are also available on the
# module itself.
#
# The main entry point for using this is the
# {Hypothesis#hypothesis} method. All of the other
# methods make sense only inside blocks passed to
# it.
module Hypothesis
  # @!visibility private
  HYPOTHESIS_LOCATION = File.dirname(__FILE__)

  # @!visibility private
  def hypothesis_stable_identifier
    # Attempt to get a "stable identifier" for any any
    # call into hypothesis. We use these to create
    # database keys (or will when we have a database) that
    # are stable across runs, so that when a test that
    # previously failed is rerun, we can fetch and reuse
    # the previous examples.

    # Note that essentially any answer to this method is
    # "fine" in that the failure mode is that sometiems we
    # just won't run the same test, but it's nice to keep
    # this as stable as possible if the code isn't changing.

    # Minitest makes it nice and easy to create a stable
    # test identifier, because it follows the classic xunit
    # pattern where a test is just a method invocation on a
    # fresh test class instance and it's easy to find out
    # which invocation that was.
    return "#{self.class.name}::#{@NAME}" if defined? @NAME

    # If we are running in an rspec example then, sadly,
    # rspec take the entirely unreasonable stance that
    # the correct way to pass data to a test is by passing
    # it as a function argument. Honestly, what is this,
    # Haskell? Ahem. Perfectly reasonable design decisions
    # on rspec's part, this creates some annoying difficulties
    # for us. We solve this through brute force and ignorance
    # by relying on the information we want being in the
    # inspect for the Example object, even if it's just there
    # as a string.
    begin
      is_rspec = is_a? RSpec::Core::ExampleGroup
      # We do our coverage testing inside rspec, so this will
      # never trigger! Though we also don't currently have a
      # test that covers it outside of rspec...
      # :nocov:
    rescue NameError
      is_rspec = false
    end
    # :nocov:

    if is_rspec
      return [
        self.class.description,
        inspect.match(/"([^"]+)"/)[1]
      ].join(' ')
    end

    # Fallback time! We just walk the stack until we find the
    # entry point into code we control. This will typically be
    # where "hypothesis" was called.
    Thread.current.backtrace.each do |line|
      return line unless line.include?(Hypothesis::HYPOTHESIS_LOCATION)
    end
    # This should never happen unless something very strange is
    # going on.
    # :nocov:
    raise 'BUG: Somehow we have no caller!'
    # :nocov:
  end

  # Run a test using Hypothesis.
  #
  # For example:
  #
  # ```ruby
  # hypothesis do
  #   x = any integer
  #   y = any integer(min: x)
  #   expect(y).to be >= x
  # end
  # ```
  #
  # The arguments to `any` are `Possible` instances which
  # specify the range of value values for it to return.
  #
  # Typically you would include this inside some test in your
  # normal testing framework - e.g. in an rspec it block or a
  # minitest test method.
  #
  # This will run the block many times with integer values for
  # x and y, and each time it will pass because we specified that
  # y had a minimum value of x.
  # If we changed it to `expect(y).to be > x` we would see output
  # like the following:
  #
  # ```
  # Failure/Error: expect(y).to be > x
  #
  # Given #1: 0
  # Given #2: 0
  # expected: > 0
  #      got:   0
  # ```
  #
  # In more detail:
  #
  # hypothesis calls its provided block many times. Each invocation
  # of the block is a *test case*.
  # A test case has three important features:
  #
  # * *givens* are the result of a call to self.any, and are the
  #   values that make up the test case. These might be values such
  #   as strings, integers, etc. or they might be values specific to
  #   your application such as a User object.
  # * *assumptions*, where you call `self.assume(some_condition)`. If
  #   an assumption fails (`some_condition` is false), then the test
  #   case is considered invalid, and is discarded.
  # * *assertions* are anything that will raise an error if the test
  #   case should be considered a failure. These could be e.g. RSpec
  #   expectations or minitest matchers, but anything that throws an
  #   exception will be treated as a failed assertion.
  #
  # A test case which satisfies all of its assumptions and assertions
  # is *valid*. A test-case which satisfies all of its assumptions but
  # fails one of its assertions is *failing*.
  #
  # A call to hypothesis does the following:
  #
  # 1. It first tries to *reuse* failing test cases for previous runs.
  # 2. If there were no previous failing test cases then it tries to
  #    *generate* new failing test cases.
  # 3. If either of the first two phases found failing test cases then
  #    it will *shrink* those failing test cases.
  # 4. Finally, it will *display* the shrunk failing test case by
  #    the error from its failing assertion, modified to show the
  #    givens of the test case.
  #
  # Reuse uses an internal representation of the test case, so examples
  # from previous runs will obey all of the usual invariants of generation.
  # However, this means that if you change your test then reuse may not
  # work. Test cases that have become invalid or passing will be cleaned
  # up automatically.
  #
  # Generation consists of randomly trying test cases until one of
  # three things has happened:
  #
  # 1. It has found a failing test case. At this point it will start
  #    *shrinking* the test case (see below).
  # 2. It has found enough valid test cases. At this point it will
  #    silently stop.
  # 3. It has found so many invalid test cases that it seems unlikely
  #    that it will find any more valid ones in a reasonable amount of
  #    time. At this point it will either silently stop or raise
  #    `Hypothesis::Unsatisfiable` depending on how many valid
  #    examples it found.
  #
  # *Shrinking* is when Hypothesis takes a failing test case and tries
  # to make it easier to understand. It does this by replacing the givens
  # in the test case with smaller and simpler values. These givens will
  # still come from the possible values, and will obey all the usual
  # constraints.
  # In general, shrinking is automatic and you shouldn't need to care
  # about the details of it. If the test case you're shown at the end
  # is messy or needlessly large, please file a bug explaining the problem!
  #
  # @param max_valid_test_cases [Integer] The maximum number of valid test
  #   cases to run without finding a failing test case before stopping.
  #
  # @param database [String, nil, false] A path to a directory where Hypothesis
  #   should store previously failing test cases. If it is nil, Hypothesis
  #   will use a default of .hypothesis/examples in the current directory.
  #   May also be set to false to disable the database functionality.
  def hypothesis(max_valid_test_cases: 200, database: nil, &block)
    unless World.current_engine.nil?
      raise UsageError, 'Cannot nest hypothesis calls'
    end
    begin
      World.current_engine = Engine.new(
        hypothesis_stable_identifier,
        max_examples: max_valid_test_cases,
        database: database
      )
      World.current_engine.run(&block)
    ensure
      World.current_engine = nil
    end
  end

  # Supplies a value to be used in your hypothesis.
  # @note It is invalid to call this method outside of a hypothesis block.
  # @return [Object] A value provided by the possible argument.
  # @param possible [Possible] A possible that specifies the possible values
  #   to return.
  # @param name [String, nil] An optional name to show next to the result on
  #   failure. This can be helpful if you have a lot of givens in your
  #   hypothesis, as it makes it easier to keep track of which is which.
  def any(possible, name: nil, &block)
    if World.current_engine.nil?
      raise UsageError, 'Cannot call any outside of a hypothesis block'
    end

    World.current_engine.current_source.any(
      possible, name: name, &block
    )
  end

  # Specify an assumption of your test case. Only test cases which satisfy
  # their assumptions will treated as valid, and all others will be
  # discarded.
  # @note It is invalid to call this method outside of a hypothesis block.
  # @note Try to use this only with "easy" conditions. If the condition is
  #   too hard to satisfy this can make your testing much worse, because
  #   Hypothesis will have to retry the test many times and will struggle
  #   to find "interesting" test cases. For example `assume(x != y)` is
  #   typically fine, and `assume(x == y)` is rarely a good idea.
  # @param condition [Boolean] The condition to assume. If this is false,
  #   the current test case will be treated as invalid and the block will
  #   exit by throwing an exception. The next test case will then be run
  #   as normal.
  def assume(condition)
    if World.current_engine.nil?
      raise UsageError, 'Cannot call assume outside of a hypothesis block'
    end
    World.current_engine.current_source.assume(condition)
  end
end
