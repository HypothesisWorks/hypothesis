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

  it 'Rutie binding tests' do
    hypothesis do
      x = any(integers)
      puts x
      puts any(arrays(of: integers)).to_s
    end
  end
end
