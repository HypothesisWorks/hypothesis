# frozen_string_literal: true

RSpec.describe 'find' do
  include Hypothesis::Debug

  # it "raises an error if it can't find anything" do
  #   expect do
  #     find do
  #       any integers
  #       false
  #     end
  #   end.to raise_exception(Hypothesis::Debug::NoSuchExample)
  # end

  it do
    hypothesis do
      puts any(arrays(of: integers)).to_s
#      puts "Debuggin"
#      puts any integers
    end
  end
end
