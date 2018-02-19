# frozen_string_literal: true

RSpec.describe 'find' do
  include Hypothesis::Debug

  it "raises an error if it can't find anything" do
    expect do
      find do
        any integers
        false
      end
    end.to raise_exception(Hypothesis::Debug::NoSuchExample)
  end
end
