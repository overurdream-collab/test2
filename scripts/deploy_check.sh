#!/usr/bin/env bash
# Read-only engineering checks. No deployment, migrations, seed or financial activation.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${MCIAS_CHECK_PYTHON:-python3}" -B "$script_dir/deploy_check.py" "$@"
