# frozen_string_literal: true

require 'helix_runtime/build_task'

begin
  require 'rspec/core/rake_task'
  RSpec::Core::RakeTask.new(:spec)

  require 'rake/testtask'

  Rake::TestTask.new(minitests: :build) do |t|
    t.test_files = FileList['minitests/**/test_*.rb']
    t.verbose = true
  end

  task test: %i[build spec minitests]
rescue LoadError
end

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

task :format do
  sh 'bundle exec rubocop -a lib spec minitests Rakefile'
end

begin
  require "yard"

  YARD::Rake::YardocTask.new(:runyard) do |t|
   t.files   = [
    'lib/hypothesis.rb', 'lib/hypothesis/errors.rb', 'lib/hypothesis/providers.rb',
    'lib/hypothesis/testcase.rb',
  ]
   t.options = ['--markup=markdown', '--no-private']
  end

  task :doc => :runyard do
    YARD::Registry.load

    objs = YARD::Registry.select do |o|
      is_private = false
      t = o
      while !t.root?
        if t.visibility != :public
          is_private = true
          break
        end
        t = t.parent
      end

      !is_private && o.docstring.blank? 
    end

    objs.sort_by!{|o| o.name.to_s }

    if objs.size > 0
      abort "Undocumented objects: #{objs.map{|o| o.name}.join(', ')}"
    end
  end
rescue LoadError
end
