# frozen_string_literal: true

require 'helix_runtime'
require 'hypothesis-ruby/native'
require 'rspec/expectations'


module Hypothesis
  class Engine
    include RSpec::Matchers

    attr_reader :current_source
    attr_accessor :is_find

    def initialize(options)
      seed = Random.rand(2**64 - 1)
      @core_engine = HypothesisCoreEngine.new(
        seed, options.fetch(:max_examples)
      )

      @exceptions_to_tags = Hash.new{|h, k| h[k] = h.size }
    end

    def run
      loop do
        core = @core_engine.new_source
        break if core.nil?
        @current_source = TestCase.new(core)
        begin
          result = yield(@current_source)
          if is_find && result
            @core_engine.finish_interesting(core, 0)
          else
            @core_engine.finish_valid(core)
          end
        rescue UnsatisfiedAssumption
          @core_engine.finish_invalid(core)
        rescue DataOverflow
          @core_engine.finish_overflow(core)
        rescue Exception => e
          raise if is_find
          key = [e.class, e.backtrace[0]] 
          @core_engine.finish_interesting(core, @exceptions_to_tags[key])
        end
      end
      if @core_engine.count_failing_examples == 0
        raise Unsatisfiable if @core_engine.was_unsatisfiable
        @current_source = nil
        return
      end

      if is_find
        core = @core_engine.failing_example(0)
        @current_source = TestCase.new(core, record_draws: true)
        yield @current_source
      else
        exceptions = []
        (0...@core_engine.count_failing_examples).each do |example|
          @current_source = TestCase.new(core, print_draws: true)

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
            if @core_engine.count_failing_examples == 1
              raise e
            else
              exceptions.push(e)
            end
          end
        end
      end
    end
  end
end
