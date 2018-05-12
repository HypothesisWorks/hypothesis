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
end
