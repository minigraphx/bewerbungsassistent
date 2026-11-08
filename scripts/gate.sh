#!/bin/sh
# Runs every test suite of the repo in parallel; this is Pullboard's gate.
# Worktrees carry no .venv of their own, so Python comes from the main checkout.
# Exit code: 0 when all suites pass, 1 otherwise.
set -u

root=$(git rev-parse --show-toplevel) || exit 1
common=$(git rev-parse --path-format=absolute --git-common-dir) || exit 1
python="$(dirname "$common")/.venv/bin/python"
if [ ! -x "$python" ]; then
  echo "gate: $python is missing; create the venv in the main checkout" >&2
  exit 1
fi

# Tests must never reach the real keychain.
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

logs=$(mktemp -d) || exit 1
trap 'rm -rf "$logs"' EXIT

run() { # name folder command...
  name=$1; folder=$2; shift 2
  ( cd "$root/$folder" && "$@" ) >"$logs/$name.log" 2>&1
  echo $? >"$logs/$name.status"
}

run desktop desktop "$python" -m pytest tests -q &
run onboarding onboarding "$python" -m pytest -q &
run lebenslauf lebenslauf "$python" -m pytest -q &
run vermittlung vermittlung "$python" -m pytest -q &
run bewerbungen bewerbungen "$python" -m pytest -q &
run onboarding-js onboarding sh -c 'node --test tests/*.test.cjs' &
run bewerbungen-js bewerbungen sh -c 'node --test tests/*.test.cjs' &
run erweiterung . sh -c 'node --test erweiterung/tests/*.test.mjs' &
wait

failed=0
for status in "$logs"/*.status; do
  name=$(basename "$status" .status)
  if [ "$(cat "$status")" = 0 ]; then
    echo "gate: $name passed"
  else
    failed=1
    echo "gate: $name FAILED"
    tail -40 "$logs/$name.log"
  fi
done
exit "$failed"
