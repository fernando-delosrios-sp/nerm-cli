.PHONY: test build dist help

test:
	go test ./...

build:
	go build -o dist/nerm ./cmd/nerm

dist:
	bash scripts/build-npm.sh

help:
	go run ./cmd/nerm --help
