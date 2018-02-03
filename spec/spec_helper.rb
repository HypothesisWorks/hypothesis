# frozen_string_literal: true

require 'hypothesis'

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
  config.include(Hypothesis::Providers)
end
