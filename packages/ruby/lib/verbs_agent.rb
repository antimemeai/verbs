# frozen_string_literal: true

module VerbsAgent
  class Violation < ArgumentError
    attr_reader :constraint

    def initialize(constraint)
      @constraint = constraint
      super("constraint violated: #{constraint}")
    end
  end

  # Evaluate a synchronous predicate once; only true passes. Errors propagate.
  def self.check(name, value)
    raise Violation, name unless yield(value).equal?(true)

    value
  end
end
