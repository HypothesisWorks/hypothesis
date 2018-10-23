# frozen_string_literal: true

RSpec.describe 'tests with multiple failures' do
  they 'show multiple failures' do
    expect do
      @initial = nil

      hypothesis do
        x = any integers
        if @initial.nil?
          if x >= 1000
            @initial = x
          else
            next
          end
        end

        expect(x).to_not eq(@initial)
        raise 'Nope'
      end
    end.to raise_exception(Hypothesis::MultipleExceptionError) { |e|
      expect(e.all_exceptions.length).to eq(2)
    }
  end
end

RSpec.describe Hypothesis::MultipleExceptionError do
  it 'includes the message from each exception' do
    exceptions = []
    %w[hello world].each do |m|
      begin
        raise m
      rescue Exception => e
        exceptions.push(e)
      end
    end

    e = Hypothesis::MultipleExceptionError.new(*exceptions)
    expect(e.message).to include('hello')
    expect(e.message).to include('world')
  end
end
