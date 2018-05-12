# frozen_string_literal: true

module Hypothesis
  # A TestCase class provides a concrete representation of
  # an executing test case. You do not normally need to use this
  # within the body of the test, but it exists to be used as
  # an argument to {Hypothesis::Possibilities::built_as}.
  # @!visibility private
  class TestCase
    # @!visibility private
    attr_reader :draws, :print_log, :print_draws, :wrapped_data

    # @!visibility private
    def initialize(wrapped_data, print_draws: false, record_draws: false)
      @wrapped_data = wrapped_data

      @draws = [] if record_draws
      @print_log = [] if print_draws
      @depth = 0
    end

    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end

    # @!visibility private
    def any(possible = nil, name: nil, &block)
      top_level = @depth.zero?

      begin
        @depth += 1
        possible ||= block
        @wrapped_data.start_draw
        result = possible.provide(&block)
        @wrapped_data.stop_draw
        if top_level
          draws&.push(result)
          print_log&.push([name, result.inspect])
        end
        result
      ensure
        @depth -= 1
      end
    end
  end
end
