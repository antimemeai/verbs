#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if [ "$#" -eq 0 ]; then
    set -- php dart ruby erlang dotnet
fi
for language in "$@"; do
    case "$language" in
        php)
            php packages/php/tests/check.php
            ;;
        dart)
            (cd packages/dart
             dart pub get
             dart analyze
             dart run test/check.dart
             dart pub publish --dry-run)
            ;;
        ruby)
            (cd packages/ruby
             ruby test/check.rb
             mkdir -p dist
             gem build verbs-agent.gemspec --output dist/verbs-agent-0.1.0.gem)
            ;;
        erlang)
            (cd packages/erlang
             mkdir -p build
             erlc -Werror -o build src/verbs_agent.erl test/verbs_agent_check.erl
             erl -noshell -pa build -eval 'ok = verbs_agent_check:run(), halt(0).')
            ;;
        dotnet)
            dotnet run --project packages/dotnet/tests/Check.csproj
            dotnet pack packages/dotnet/Verbs.csproj --configuration Release \
                --output packages/dotnet/dist
            ;;
        *)
            echo "Unknown language: $language" >&2
            exit 2
            ;;
    esac
done
