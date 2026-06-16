#!/usr/bin/env bash
set -euo pipefail

make py-lint
make py-test
