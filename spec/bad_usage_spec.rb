# frozen_string_literal: true

def bad_usage(&block)
  expect(&block).to raise_exception(Hypothesis::UsageError)
end

RSpec.describe 'Incorrect usage' do
  it 'includes nesting hypothesis calls' do
    bad_usage do
      hypothesis do
        hypothesis do
        end
      end
    end
  end

  it 'includes using given outside a hypothesis call' do
    bad_usage { given integers }
  end

  it 'includes using assume outside a hypothesis call' do
    bad_usage { assume true }
  end

  it 'includes using find inside a hypothesis' do
    class <<self
      include Hypothesis::Debug
    end
    bad_usage do
      hypothesis do
        find { given integers >= 0 }
      end
    end
  end
end
