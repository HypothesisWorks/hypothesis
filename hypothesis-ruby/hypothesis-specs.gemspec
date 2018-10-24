# frozen_string_literal: true

Gem::Specification.new do |s|
  s.name        = 'hypothesis-specs'
  s.version     = '0.2.0'
  s.date        = '2018-10-24'
  s.description = <<~DESCRIPTION
    Hypothesis is a powerful, flexible, and easy to use library for property-based testing.
DESCRIPTION
  s.summary     = s.description
  s.authors     = ['David R. Maciver']
  s.email       = 'david@drmaciver.com'
  s.files       = Dir['{ext/*,src/**/*,lib/**/*}'] + [
    'Cargo.toml', 'LICENSE.txt', 'README.markdown', 'Rakefile',
    'CHANGELOG.md'
  ]
  s.homepage    = 'https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis-ruby'
  s.license     = 'MPL-2.0'
  s.extensions = Dir['ext/extconf.rb']
  s.add_dependency 'helix_runtime', '~> 0.7.0'
  s.add_runtime_dependency 'rake', '>= 10.0', '< 13.0'
end
