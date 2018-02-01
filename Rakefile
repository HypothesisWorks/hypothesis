# frozen_string_literal: true

require 'bundler/setup'

require 'rspec/core/rake_task'
require 'rubocop/rake_task'
require 'helix_runtime/build_task'

RSpec::Core::RakeTask.new(:test)

RuboCop::RakeTask.new

# Monkeypatch build to fail on error.
# See https://github.com/tildeio/helix/issues/133
module HelixRuntime
  class Project
    alias original_build cargo_build

    def cargo_build
      raise 'Build failed' unless original_build
    end
  end
end

HelixRuntime::BuildTask.new

task test: :build

task :format do
  sh 'bundle exec rubocop -a'
end
