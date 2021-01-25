# frozen_string_literal: true

require 'simplecov'
SimpleCov.minimum_coverage 100

class PrintingFormatter
  # Takes a SimpleCov::Result and generates a string out of it
  def format(result)
    bad = []
    result.files.each do |file|
      bad.push file if file.covered_percent < 100.0
    end

    unless bad.empty?
      puts 'Files with missing coverage!'
      bad.each do |file|
        lines = file.source_lines.select { |l| l.coverage == 0 }
                    .map(&:line_number).sort
        s = lines[0]
        groups = [[s, s]]
        lines.each do |i|
          if i <= groups[-1][-1] + 1
            groups[-1][-1] = i
          else
            groups.push([i, i])
          end
        end
        markers = []
        groups.each do |g|
          if g[0] == g[1]
            markers.push(g[0].to_s)
          else
            markers.push(g.join('-'))
          end
        end
        puts "#{file.filename}: #{markers.join(', ')}"
      end
    end
  end
end

SimpleCov.formatters = SimpleCov::Formatter::MultiFormatter.new(
  [SimpleCov::Formatter::HTMLFormatter, PrintingFormatter]
)

SimpleCov.start do
  add_filter do |source_file|
    name = source_file.filename
    !(name.include?('/hypothesis-ruby/lib/') || name.end_with?('hypothesis.rb'))
  end
end

require 'hypothesis'

module Hypothesis
  module Debug
    class NoSuchExample < HypothesisError
    end

    def find(options = {}, &block)
      unless Hypothesis::World.current_engine.nil?
        raise UsageError, 'Cannot nest hypothesis calls'
      end
      begin
        Hypothesis::World.current_engine = Hypothesis::Engine.new(
          'find',
          max_examples: options.fetch(:max_examples, 1000),
          phases: options.fetch(:phases, Phase.all)
        )
        Hypothesis::World.current_engine.is_find = true
        Hypothesis::World.current_engine.run(&block)
        source = Hypothesis::World.current_engine.current_source
        raise NoSuchExample if source.nil?
        source.draws
      ensure
        Hypothesis::World.current_engine = nil
      end
    end

    def find_any(options = {}, &block)
      # Currently the same as find, but once we have config
      # options for shrinking it will turn that off.
      find(options, &block)
    end
  end
end

RSpec.configure do |config|
  config.expect_with :rspec do |expectations|
    expectations.include_chain_clauses_in_custom_matcher_descriptions = true
  end

  config.alias_example_to :they

  config.mock_with :rspec do |mocks|
    mocks.verify_partial_doubles = true
  end

  config.shared_context_metadata_behavior = :apply_to_host_groups

  config.example_status_persistence_file_path = 'spec/examples.txt'
  config.disable_monkey_patching!

  config.warnings = true

  config.default_formatter = 'doc'

  config.profile_examples = 10

  config.order = :random

  Kernel.srand config.seed

  config.include(Hypothesis)
  config.include(Hypothesis::Possibilities)

  config.before(:each) do
    FileUtils.rm_rf Hypothesis::DEFAULT_DATABASE_PATH
  end
end
