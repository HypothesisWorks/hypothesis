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
        core = @core_engine.new_source
        break if core.nil?
        @current_source = Source.new(core)
        begin
          result = yield(@current_source)
          if is_find && result
            @core_engine.finish_interesting(core)
          else
            @core_engine.finish_valid(core)
          end
        rescue UnsatisfiedAssumption
          @core_engine.finish_invalid(core)
        rescue DataOverflow
          @core_engine.finish_overflow(core)
        rescue Exception
          raise if is_find
          @core_engine.finish_interesting(core)
        end
      end
      core = @core_engine.failing_example
      if core.nil?
        raise Unsatisfiable if @core_engine.was_unsatisfiable
        return
      end

      if is_find
        @current_source = Source.new(core, record_draws: true)
        yield @current_source
      else
        @current_source = Source.new(core, print_draws: true)

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
    attr_reader :draws, :print_log, :print_draws, :wrapped_data

    def initialize(wrapped_data, print_draws: false, record_draws: false)
      @wrapped_data = wrapped_data

      @draws = [] if record_draws
      @print_log = [] if print_draws
    end

    def given(provider)
      result = local_given(provider)
      draws&.push(result)
      result
    end

    def given(provider = nil, name: nil, &block)
      provider ||= block
      result = provider.provide(self)
      draws&.push(result)
      print_log&.push([name, result.inspect])
      result
    end

    def local_given(provider)
      provider.provide(self)
    end

    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end
  end
end
