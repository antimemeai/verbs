# frozen_string_literal: true

require_relative '../lib/verbs_agent'

def expect(condition)
  raise 'contract test failed' unless condition
end

(-10..10).each do |n|
  begin
    result = VerbsAgent.check('bounded', n) { |v| (1..5).cover?(v) }
    expect((1..5).cover?(n) && result == n)
  rescue VerbsAgent::Violation => error
    expect(!(1..5).cover?(n))
    expect(error.constraint == 'bounded')
    expect(error.message == 'constraint violated: bounded')
  end
end
value = []
calls = 0
result = VerbsAgent.check('same', value) { calls += 1; true }
expect(result.equal?(value) && calls == 1)
sentinel = RuntimeError.new('predicate failed')
begin
  VerbsAgent.check('broken', 0) { raise sentinel }
  raise 'predicate error was swallowed'
rescue RuntimeError => error
  expect(error.equal?(sentinel))
end
[1, 'true', [], {}, nil].each do |invalid|
  begin
    VerbsAgent.check('boolean', 0) { invalid }
    raise 'non-boolean accepted'
  rescue VerbsAgent::Violation => error
    expect(error.constraint == 'boolean')
  end
end
puts 'Ruby contract checks passed'
