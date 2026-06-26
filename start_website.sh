#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
printf '%s\n' 'De website is beschikbaar op http://localhost:8000'
python3 -m http.server 8000
