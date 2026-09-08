#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT

cat >"$test_dir/kubectl" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == create ]]; then
  printf '%s\n' 'apiVersion: v1' 'kind: Namespace' 'metadata:' '  name: dev'
elif [[ "$1" == apply ]]; then
  cat >/dev/null
elif [[ "$1" == get && "$2" == secret && " $* " == *" -o jsonpath="* ]]; then
  printf %s 'c3FsaXRlOi8vL2RhdGFiYXNlLmRi'
elif [[ "$1" == get && "$2" == secret ]]; then
  exit 0
else
  echo "unexpected kubectl call: $*" >&2
  exit 99
fi
SH
chmod +x "$test_dir/kubectl"

if PATH="$test_dir:$PATH" "$repo_root/deploy/deploy.sh" dev >"$test_dir/output" 2>&1; then
  echo "SQLite DB_URL이 거부되지 않았습니다." >&2
  exit 1
fi
grep -q 'PostgreSQL' "$test_dir/output"
