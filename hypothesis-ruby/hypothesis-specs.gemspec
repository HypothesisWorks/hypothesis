# frozen_string_literal: true

Gem::Specification.new do |s|
  s.name        = 'hypothesis-specs'
  s.version     = '0.7.1'
  s.date        = '2021-03-27'
  s.description = <<~DESCRIPTION
    Hypothesis is a powerful, flexible, and easy to use library for property-based testing.
DESCRIPTION
  s.summary     = s.description
  s.authors     = ['David R. Maciver', 'Alex Weisberger']
  s.email       = 'david@drmaciver.com'
  s.files       = Dir['{ext/*,src/**/*,lib/**/*}'] + [
    'Cargo.toml', 'LICENSE.txt', 'README.markdown', 'Rakefile',
    'CHANGELOG.md'
  ]
  s.homepage    = 'https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis-ruby'
  s.license     = 'MPL-2.0'
  s.extensions = Dir['ext/extconf.rb']
  s.add_dependency 'rutie', '~> 0.0.3'
end
