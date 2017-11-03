# frozen_string_literal: true

require 'bundler/setup'

require 'rspec/core/rake_task'
require 'rubocop/rake_task'
require 'helix_runtime/build_task'

RSpec::Core::RakeTask.new(:test)

RuboCop::RakeTask.new

HelixRuntime::BuildTask.new

task :test => :build

