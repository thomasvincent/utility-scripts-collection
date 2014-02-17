#!/bin/bash

# Pretty print JSON. Requires perl and the JSON module from CPAN.
# From: https://github.com/micha/resty/blob/master/pp

perl -0007 -MJSON -ne'print to_json(from_json($_, {allow_nonref=>1}),{pretty=>1})."\n"'

