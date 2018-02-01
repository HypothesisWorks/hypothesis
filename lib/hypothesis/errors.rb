# frozen_string_literal: true

module Hypothesis
  class Error < RuntimeError
  end

  class Unsatisfiable < Error
  end

  class UnsatisfiedAssumption < Error
  end

  class DataOverflow < Error
  end

  class UsageError < Error
  end
end
