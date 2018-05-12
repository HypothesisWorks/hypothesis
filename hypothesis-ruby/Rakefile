# frozen_string_literal: true

require 'rubygems'
require 'helix_runtime/build_task'
require 'date'
require 'open3'

begin
  require 'rspec/core/rake_task'
  RSpec::Core::RakeTask.new(:spec)

  require 'rake/testtask'

  Rake::TestTask.new(minitests: :build) do |t|
    t.test_files = FileList['minitests/**/test_*.rb']
    t.verbose = true
  end

  task :rust_tests do
    sh 'cargo test'
  end

  task test: %i[build spec minitests rust_tests]
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

def rubocop(fix:)
  sh "bundle exec rubocop #{'-a' if fix} lib spec minitests " \
  'Rakefile hypothesis-specs.gemspec'
end

task :checkformat do
  rubocop(fix: false)
end

task :format do
  rubocop(fix: true)
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

GEMSPEC = 'hypothesis-specs.gemspec'

RELEASE_FILE = 'RELEASE.md'
CHANGELOG = 'CHANGELOG.md'

def run_for_output(*args)
  out, result = Open3.capture2(*args)
  abort if result.exitstatus != 0
  out.strip
end

task :gem do
  uncommitted = `git ls-files lib/ --others --exclude-standard`.split
  uncommitted_ruby = uncommitted.grep(/\.rb$/)
  uncommitted_ruby.sort!
  unless uncommitted_ruby.empty?
    abort 'Cannot build gem with uncomitted Ruby '\
      "files #{uncommitted_ruby.join(', ')}"
  end

  spec = Gem::Specification.load(GEMSPEC)

  unless system 'git', 'diff', '--exit-code', *(spec.files - ['Rakefile'])
    abort 'Cannot build gem from uncommited files'
  end

  previous_version = spec.version.to_s

  if run_for_output('git', 'tag', '-l', previous_version).empty?
    sh 'git', 'fetch', '--tags'
  end

  point_of_divergence = run_for_output(
    'git', 'merge-base', 'HEAD', previous_version
  )

  has_changes = !system("git diff --exit-code #{point_of_divergence} "\
    '-- src/ lib/')
  if File.exist?(RELEASE_FILE)
    release_contents = IO.read(RELEASE_FILE).strip
    release_type, release_contents = release_contents.split("\n", 2)

    match = /RELEASE_TYPE: +(major|minor|patch)/.match(release_type)
    if match
      release_type = match[1]
      release_contents = release_contents.strip
    else
      abort "Invalid release type line #{release_type.inspect}"
    end

    components = spec.version.segments.to_a
    if release_type == 'major'
      components[0] += 1
    elsif release_type == 'minor'
      components[1] += 1
    else
      if release_type != 'patch'
        raise "Unexpected release type #{release_type.inspect}"
      end
      components[2] += 1
    end

    new_version = components.join('.')
    new_date = Date.today.strftime

    lines = File.readlines(GEMSPEC).map do |l|
      l.sub(/(s.version += +)'.+$/, "\\1'#{new_version}'").sub(
        /(s.date += +)'.+$/, "\\1'#{new_date}'"
      )
    end

    out = File.new(GEMSPEC, 'w')
    lines.each do |l|
      out.write(l)
    end
    out.close

    git 'checkout', 'HEAD', CHANGELOG
    previous_changelog = IO.read(CHANGELOG)

    out = File.new(CHANGELOG, 'w')

    out.write(
      "## Hypothesis for Ruby #{new_version} (#{new_date})\n\n"
    )
    out.write(release_contents.strip)
    out.write("\n\n")
    out.write(previous_changelog)
    out.close

    git 'reset'
    git 'add', CHANGELOG, GEMSPEC
    git 'rm', RELEASE_FILE
    git 'commit', '-m', "Bump version to #{new_version} and "\
      "update changelog\n\n[skip ci]"
  elsif has_changes
    abort 'Source changes found but no release file exists'
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
  Gem::Specification._clear_load_cache
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
    'git push ssh-origin HEAD:master && git push ssh-origin --tags'
  )

  sh 'rm -f ~/.gem/credentials'
  sh 'mkdir -p ~/.gem'
  sh 'ln -s $(pwd)/secrets/api_key.yaml ~/.gem/credentials'
  sh 'chmod 0600 ~/.gem/credentials'
  sh 'gem push hypothesis-specs*.gem'
end
