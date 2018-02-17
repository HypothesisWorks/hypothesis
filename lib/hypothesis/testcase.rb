# frozen_string_literal: true

module Hypothesis
  # A TestCase class provides a concrete representation of
  # an executing test case. You do not normally need to use this
  # within the body of the test, but it exists to be used as
  # an argument to {Hypothesis::Providers::composite}.
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

    # Calls {Hypothesis#given} in the test case this represents,
    # but does not print the result in the event of a failing test
    # case.
    #
    # @return [Object] A given for the current test case.
    # @param provider [Provider] A provider describing the possible
    #   givens.
    def given(provider)
      internal_given(provider)
    end

    # Calls {Hypothesis#assume} in the test case this represents.
    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end

    # @!visibility private
    def internal_given(provider = nil, name: nil, &block)
      top_level = @depth.zero?

      begin
        @depth += 1
        provider ||= block
        result = provider.provide(self, &block)
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
