# frozen_string_literal: true

module Hypothesis
  class HypothesisError < RuntimeError
  end

  class Unsatisfiable < HypothesisError
  end

  class UnsatisfiedAssumption < HypothesisError
  end

  class DataOverflow < HypothesisError
  end

  class UsageError < HypothesisError
  end
end
