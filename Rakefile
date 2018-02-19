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
  sh 'bundle exec rubocop -a lib spec minitests ' \
  'Rakefile hypothesis-specs.gemspec'
end

begin
  require 'yard'

  YARD::Rake::YardocTask.new(:runyard) do |t|
    t.files = [
      'lib/hypothesis.rb', 'lib/hypothesis/errors.rb',
      'lib/hypothesis/possible.rb'
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

def git(*args)
  sh 'git', *args
end

file 'secrets.tar.enc' => 'secrets' do
  sh 'rm -f secrets.tar secrets.tar.enc'
  sh 'tar -cf secrets.tar secrets'
  sh 'travis encrypt-file secrets.tar'
end

task deploy: :gem do
  on_master = system("git merge-base  --is-ancestor HEAD origin/master")

  unless on_master
    puts 'Not on master, so no deploy'
    next
  end

  spec = Gem::Specification.load('hypothesis-specs.gemspec')

  succeeded = system('git', 'tag', spec.version.to_s)

  unless succeeded
    puts "Looks like we've already done this release."
    next
  end

  unless File.directory? 'secrets'
    sh 'rm -rf secrets'
    sh 'openssl aes-256-cbc -K $encrypted_b0055249143b_key -iv ' \
    '$encrypted_b0055249143b_iv -in secrets.tar.enc -out secrets.tar -d'

    sh 'tar -xvf secrets.tar'
  end

  git('config', 'user.name', 'Travis CI on behalf of David R. MacIver')
  git('config', 'user.email', 'david@drmaciver.com')
  git('config', 'core.sshCommand', 'ssh -i secrets/deploy_key')
  git(
    'remote', 'add', 'ssh-origin',
    'git@github.com:HypothesisWorks/hypothesis-ruby.git'
  )

  sh(
    'ssh-agent', 'sh', '-c',
    'chmod 0600 secrets/deploy_key && ssh-add secrets/deploy_key && ' \
    'git push ssh-origin --tags'
  )

  sh 'rm -f ~/.gem/credentials'
  sh 'mkdir -p ~/.gem'
  sh 'ln -s $(pwd)/secrets/api_key.yaml ~/.gem/credentials'
  sh 'chmod 0600 ~/.gem/credentials'
  sh 'gem push hypothesis-specs*.gem'
end
