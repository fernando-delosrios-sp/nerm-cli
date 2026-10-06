# NERM CLI

Go CLI for SailPoint Non-Employee Risk Management (NERM) APIs, plus an agent skill that drives it.

## Install

Skill:

```bash
npx skills add sailpoint-se/tool-nerm-mcp-server@nerm-cli
```

CLI:

```bash
npm install -g nerm-cli
nerm version
```

Or run once with `npx nerm-cli`.

## Connection profiles

```bash
nerm connection add lab --url https://tenant.nonemployee.com --token "$NERM_TOKEN" --use
nerm connection test
```

The profile URL is stored under the OS config directory (`nerm-cli/config.json`). The bearer token is stored in the OS credential store (macOS Keychain, Windows Credential Manager, Linux Secret Service). If no keychain is available, use `--token-env VAR` instead. Tokens are never written to the config file.

## Common commands

```bash
nerm profile-types list --name Assignment
nerm profiles list --profile-type-id <id> --limit 20
nerm users list --name "Jane Doe"
nerm search run --body-file search.json
nerm api request GET /profiles --query 'query[limit]=1'
```

All commands print JSON on stdout. Pass `--profile <name>` to select a non-default profile. See [skills/nerm-cli/reference.md](skills/nerm-cli/reference.md) for the full catalog.

## Develop

```bash
go test ./...
make dist
node npm/nerm-cli/bin/nerm.js --help
```

`make dist` cross-compiles static binaries for darwin, linux, and windows (amd64 and arm64) into npm platform packages under `npm/packages/`.
