# frozen_string_literal: true

require 'helix_runtime'
require 'hypothesis-ruby-core/native'

module Hypothesis
  class Engine
    attr_reader :current_source
    attr_accessor :is_find

    def initialize(max_examples: 200, seed: nil)
      seed = Random.rand(2**64 - 1) if seed.nil?
      @core_engine = HypothesisCoreEngine.new(seed, max_examples)
    end

    def run
      while @core_engine.should_continue
        core_id = @core_engine.new_source
        break if core_id.nil?
        @current_source = Source.new(@core_engine, core_id)
        begin
          result = yield(@current_source)
          @core_engine.finish_interesting(core_id) if is_find && result
        rescue UnsatisfiedAssumption
          @core_engine.finish_invalid(core_id)
        rescue DataOverflow
          @core_engine.finish_overflow(core_id)
        rescue StandardError
          raise if is_find
          @core_engine.finish_interesting(core_id)
        else
          @core_engine.finish_valid(core_id)
        end
      end
      raise Unsatisfiable if @core_engine.was_unsatisfiable
      core_id = @core_engine.failing_example
      return if core_id.nil?

      @current_source = Source.new(@core_engine, core_id, record_draws: is_find)
      yield @current_source
    end
  end

  class Source
    attr_reader :draws

    def initialize(core_engine, core_id, record_draws: false)
      @core_engine = core_engine
      @core_id = core_id

      @draws = [] if record_draws
    end

    def bits(n)
      result = @core_engine.bits(@core_id, n)
      raise Hypothesis::DataOverflow if result.nil?
      result
    end

    def given(provider = nil, &block)
      provider ||= block
      result = provider.call(self)
      draws&.push(result)
      result
    end

    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end
  end
end
