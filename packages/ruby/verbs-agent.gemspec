Gem::Specification.new do |spec|
  spec.name = 'verbs-agent'
  spec.version = '0.1.0'
  spec.summary = 'Explicit, named constraints for more verifiable agent-written code'
  spec.description = 'Evaluate a named predicate once; return the original value or raise a named violation.'
  spec.authors = ['Patrick Beam']
  spec.homepage = 'https://github.com/antimemeai/verbs'
  spec.license = 'MIT'
  spec.required_ruby_version = '>= 2.6'
  spec.files = ['lib/verbs_agent.rb', 'README.md', 'LICENSE']
  spec.require_paths = ['lib']
  spec.metadata['source_code_uri'] = 'https://github.com/antimemeai/verbs/tree/main/packages/ruby'
end
