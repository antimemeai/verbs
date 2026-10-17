# Verbs for Ruby

Provisional gem identity: `verbs-agent`; not published. The existing `verbs`
gem is an unrelated conjugation library. Ruby 2.6 or newer; no dependencies.

```ruby
require 'verbs_agent'
retries = VerbsAgent.check('bounded retries', 3) { |n| (1..5).cover?(n) }
```

The block runs once. Only true passes; rejection raises VerbsAgent::Violation
with its constraint name. Block exceptions propagate. The original object is
returned. Later mutation can invalidate a check. Values stay out of errors.
The 0.1.0 API is experimental and MIT licensed.

Run `ruby test/check.rb` and `gem build verbs-agent.gemspec` here.
