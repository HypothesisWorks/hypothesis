# frozen_string_literal: true

class SomeClass
  include Hypothesis
  def stuff
    hypothesis_stable_identifier
  end
end

RSpec.describe 'stable identifiers' do
  it 'are the full rspec string' do
    expect(hypothesis_stable_identifier).to eq(
      'stable identifiers are the full rspec string'
    )
  end

  it 'fall back to a traceback' do
    ident = SomeClass.new.stuff
    expect(ident).to include(__FILE__)
    expect(ident).to include('6')
  end
end
