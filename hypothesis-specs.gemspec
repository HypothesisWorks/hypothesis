# frozen_string_literal: true

Gem::Specification.new do |s|
  s.name        = 'hypothesis-specs'
  s.version     = '0.0.1'
  s.date        = '2017-11-02'
  s.summary     = ''
  s.description = <<~DESCRIPTION
    A port of the Hypothesis property-based testing library to Ruby
DESCRIPTION
  s.authors     = ['David R. Maciver']
  s.email       = 'david@drmaciver.com'
  s.files       = [
    'lib/hypothesis.rb',
    'lib/hypothesis/*.rb'
  ]
  s.homepage    = 'http://github.com/HypothesisWorks/hypothesis-ruby'
  s.license     = 'MPL v2'
end
