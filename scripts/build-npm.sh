#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-0.1.3}"
MODULE="github.com/sailpoint-se/nerm-cli/internal/cli.Version=${VERSION}"

targets=(
  "darwin amd64 darwin-x64"
  "darwin arm64 darwin-arm64"
  "linux amd64 linux-x64"
  "linux arm64 linux-arm64"
  "windows amd64 win32-x64"
  "windows arm64 win32-arm64"
)

mkdir -p "$ROOT/dist"

for entry in "${targets[@]}"; do
  read -r goos goarch npmplat <<<"$entry"
  ext=""
  if [[ "$goos" == "windows" ]]; then
    ext=".exe"
  fi
  outdir="$ROOT/npm/packages/cli-${npmplat}"
  mkdir -p "$outdir/bin"
  CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" go build -trimpath -ldflags "-s -w -X ${MODULE}" -o "$outdir/bin/nerm${ext}" "$ROOT/cmd/nerm"
  cat > "$outdir/package.json" <<EOF
{
  "name": "@nerm-cli/${npmplat}",
  "version": "${VERSION}",
  "os": ["${npmplat%%-*}"],
  "cpu": ["${npmplat#*-}"],
  "files": ["bin"],
  "license": "UNLICENSED"
}
EOF
done

host_os="$(go env GOOS)"
host_arch="$(go env GOARCH)"
host_ext=""
host_plat=""
case "${host_os}-${host_arch}" in
  darwin-arm64) host_plat="darwin-arm64" ;;
  darwin-amd64) host_plat="darwin-x64" ;;
  linux-arm64) host_plat="linux-arm64" ;;
  linux-amd64) host_plat="linux-x64" ;;
  windows-amd64) host_plat="win32-x64"; host_ext=".exe" ;;
  windows-arm64) host_plat="win32-arm64"; host_ext=".exe" ;;
esac
if [[ -n "$host_plat" ]]; then
  cp "$ROOT/npm/packages/cli-${host_plat}/bin/nerm${host_ext}" "$ROOT/npm/nerm-cli/bin/nerm${host_ext}"
fi
