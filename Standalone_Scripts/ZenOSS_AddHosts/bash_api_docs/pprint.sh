#!/bin/bash
#
# Pretty prints JSON data.
#
# This script formats JSON data for better readability using Perl's JSON module.
# It accepts JSON input from stdin and outputs formatted JSON to stdout.
#
# Dependencies:
#   - perl
#   - JSON module from CPAN
#
# Usage:
#   cat file.json | ./pprint.sh
#   echo '{"key":"value"}' | ./pprint.sh
#
# Source: Adapted from https://github.com/micha/resty/blob/master/pp

# Validate dependencies
if ! perl -MJSON -e 'print "JSON module found\n";' &>/dev/null; then
  echo "Error: Perl JSON module not found. Please install it with: cpan JSON" >&2
  exit 1
fi

# Process JSON input
perl -0007 -MJSON -ne 'print to_json(from_json($_, {allow_nonref=>1}), {pretty=>1})."\n"'

