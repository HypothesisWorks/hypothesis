# frozen_string_literal: true

module Hypothesis
  # A generic superclass for all errors thrown by
  # Hypothesis.
  class HypothesisError < RuntimeError
  end

  # Indicates that Hypothesis was not able to find
  # enough valid examples for the test to be meaningful.
  # (Currently this is only thrown if Hypothesis did not
  # find *any* valid examples).
  class Unsatisfiable < HypothesisError
  end

  # Indicates that the Hypothesis API has been used
  # incorrectly in some manner.
  class UsageError < HypothesisError
  end

  # @!visibility private
  class UnsatisfiedAssumption < HypothesisError
  end

  # @!visibility private
  class DataOverflow < HypothesisError
  end

  if defined?(RSpec::Core::MultipleExceptionError)
    MultipleExceptionErrorParent = RSpec::Core::MultipleExceptionError
  # :nocov:
  else
    class MultipleExceptionErrorParent < StandardError
      def initialize(*exceptions)
        super()

        @all_exceptions = exceptions.to_a
      end

      attr_reader :all_exceptions
    end
  end

  class MultipleExceptionError < MultipleExceptionErrorParent
    def message
      jd = HypothesisJunkDrawer
      "Test raised #{all_exceptions.length} distinct errors:\n\n" +
        all_exceptions.map do |e|
          location = jd.find_first_relevant_line(e.backtrace).sub(/:in.+$/, '')
          backtrace = jd.prune_backtrace(e.backtrace)
          "#{e.class} at #{location}:\n" \
            "#{e.message}\n#{backtrace.map { |s| '  ' + s }
              .join("\n")}"
        end.join("\n\n")
    end

    def backtrace
      []
    end
  end
end
