#!/usr/bin/env bash
# Rebuild the page from the design source and push it live in one step.
# Run this after dropping a new bg.png in, or after re-pulling the design.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
# The in-repo copy, so a clone on any machine works without extra setup.
./deploy/tv-deploy.sh --dir dist
