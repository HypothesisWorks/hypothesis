# frozen_string_literal: true

module Hypothesis
  # @!visibility private
  module HypothesisJunkDrawer
    HYPOTHESIS_ROOT = File.absolute_path(File.dirname(__FILE__))

    def self.prune_backtrace(backtrace)
      result = []
      seen_hypothesis = false
      backtrace.each do |b|
        if b.start_with?(HYPOTHESIS_ROOT)
          seen_hypothesis = true
        else
          result.push(b)
          break if seen_hypothesis
        end
      end
      result
    end

    def self.find_first_relevant_line(backtrace)
      backtrace.each do |b|
        next if b.include?('minitest/assertions.rb')
        next if b.start_with?(HYPOTHESIS_ROOT)
        return b
      end
      nil
    end
  end
end
