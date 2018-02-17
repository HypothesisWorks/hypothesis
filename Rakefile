# frozen_string_literal: true

require 'rubygems'
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
  require 'yard'

  YARD::Rake::YardocTask.new(:runyard) do |t|
    t.files = [
      'lib/hypothesis.rb', 'lib/hypothesis/errors.rb',
      'lib/hypothesis/providers.rb', 'lib/hypothesis/testcase.rb'
    ]
    t.options = ['--markup=markdown', '--no-private']
  end

  task doc: :runyard do
    YARD::Registry.load

    objs = YARD::Registry.select do |o|
      is_private = false
      t = o
      until t.root?
        if t.visibility != :public
          is_private = true
          break
        end
        t = t.parent
      end

      !is_private && o.docstring.blank?
    end

    objs.sort_by! { |o| o.name.to_s }

    unless objs.empty?
      abort "Undocumented objects: #{objs.map(&:name).join(', ')}"
    end
  end
rescue LoadError
end

task :gem do
  uncommitted = `git ls-files lib/ --others --exclude-standard`.split
  uncommitted_ruby = uncommitted.grep(/\.rb$/)
  uncommitted_ruby.sort!
  unless uncommitted_ruby.empty?
    abort 'Cannot build gem with uncomitted Ruby '\
      "files #{uncommitted_ruby.join(', ')}"
  end

  sh 'rm -rf hypothesis-specs*.gem'
  sh 'git clean -fdx lib'
  sh 'gem build hypothesis-specs.gemspec'
end

task :tag_release do
  spec = Gem::Specification.load('hypothesis-specs.gemspec')
  sh 'git', 'tag', spec.version.to_s
end
