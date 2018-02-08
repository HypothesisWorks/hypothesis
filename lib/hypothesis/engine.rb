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
      loop do
        core_id = @core_engine.new_source
        break if core_id.nil?
        @current_source = Source.new(@core_engine, core_id)
        begin
          result = yield(@current_source)
          if is_find && result
            @core_engine.finish_interesting(core_id)
          else
            @core_engine.finish_valid(core_id)
          end
        rescue UnsatisfiedAssumption
          @core_engine.finish_invalid(core_id)
        rescue DataOverflow
          @core_engine.finish_overflow(core_id)
        rescue Exception
          raise if is_find
          @core_engine.finish_interesting(core_id)
        end
      end
      core_id = @core_engine.failing_example
      if core_id.nil?
        raise Unsatisfiable if @core_engine.was_unsatisfiable
        return
      end

      if is_find
        @current_source = Source.new(@core_engine, core_id, record_draws: true)
        yield @current_source
      else
        @current_source = Source.new(@core_engine, core_id, print_draws: true)

        begin
          yield @current_source
        rescue Exception => e
          givens = @current_source.print_log
          given_str = givens.each_with_index.map do |(name, s), i|
            name = "##{i + 1}" if name.nil?
            "Given #{name}: #{s}"
          end.to_a

          if e.respond_to? :hypothesis_data
            e.hypothesis_data[0] = given_str
          else
            original_to_s = e.to_s
            original_inspect = e.inspect

            class <<e
              attr_accessor :hypothesis_data

              def to_s
                ['', hypothesis_data[0], '', hypothesis_data[1]].join("\n")
              end

              def inspect
                ['', hypothesis_data[0], '', hypothesis_data[2]].join("\n")
              end
            end
            e.hypothesis_data = [given_str, original_to_s, original_inspect]
          end
          raise e
        end
      end
    end
  end

  class Source
    attr_reader :draws, :print_log, :print_draws

    def initialize(
      core_engine, core_id, print_draws: false, record_draws: false
    )
      @core_engine = core_engine
      @core_id = core_id

      @draws = [] if record_draws
      @print_log = [] if print_draws
    end

    def bits(n)
      result = @core_engine.bits(@core_id, n)
      raise Hypothesis::DataOverflow if result.nil?
      result
    end

    def given(provider = nil, name: nil, &block)
      provider ||= block
      result = provider.call(self)
      draws&.push(result)
      print_log&.push([name, result.inspect])
      result
    end

    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end
  end
end
