#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=""
DO_GIT=0
DRY_RUN=0
PLATS=(darwin-arm64 darwin-x64 linux-arm64 linux-x64 win32-arm64 win32-x64)

usage() {
  cat <<'EOF'
Publish nerm-cli and platform binaries to the configured npm registry.

Usage:
  scripts/publish-npm.sh <version> [--git] [--dry-run]

Examples:
  scripts/publish-npm.sh 0.1.1
  scripts/publish-npm.sh 0.1.1 --git
  make publish VERSION=0.1.1
EOF
}

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    --git)
      DO_GIT=1
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$arg"
      else
        echo "unexpected argument: $arg" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "version is required" >&2
  usage >&2
  exit 1
fi
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "invalid version: $VERSION" >&2
  exit 1
fi

python3 - "$ROOT" "$VERSION" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
version = sys.argv[2]

pkg_path = root / "npm" / "nerm-cli" / "package.json"
pkg = json.loads(pkg_path.read_text())
pkg["version"] = version
for name in pkg.get("optionalDependencies", {}):
    pkg["optionalDependencies"][name] = version
pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")

build = root / "scripts" / "build-npm.sh"
text = build.read_text()
text, n = re.subn(
    r'VERSION="\$\{VERSION:-[^}]+\}"',
    f'VERSION="${{VERSION:-{version}}}"',
    text,
    count=1,
)
if n != 1:
    raise SystemExit("could not update VERSION default in scripts/build-npm.sh")
build.write_text(text)

go_file = root / "internal" / "cli" / "root.go"
text = go_file.read_text()
text, n = re.subn(
    r'var Version = "[^"]+"',
    f'var Version = "{version}"',
    text,
    count=1,
)
if n != 1:
    raise SystemExit("could not update Version in internal/cli/root.go")
go_file.write_text(text)
PY

echo "Bumped version to $VERSION"
VERSION="$VERSION" bash "$ROOT/scripts/build-npm.sh"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run: skipping npm publish"
  exit 0
fi

for plat in "${PLATS[@]}"; do
  echo "Publishing @nerm-cli/${plat}@$VERSION"
  npm publish "$ROOT/npm/packages/cli-$plat" --access public
done

echo "Publishing nerm-cli@$VERSION"
npm publish "$ROOT/npm/nerm-cli" --access public

if [[ "$DO_GIT" -eq 1 ]]; then
  git -C "$ROOT" add npm/nerm-cli/package.json scripts/build-npm.sh internal/cli/root.go
  git -C "$ROOT" commit -m "Release ${VERSION}"
  git -C "$ROOT" tag "v${VERSION}"
  git -C "$ROOT" push nerm-cli HEAD --tags
fi

echo "Published nerm-cli@$VERSION"
