#!/bin/sh
tmpfile=$(mktemp)
tr -d '\r' <"$1" >"$tmpfile"
mv "$tmpfile" "$1"
