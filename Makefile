.PHONY: test build dist help publish

test:
	go test ./...

build:
	go build -o dist/nerm ./cmd/nerm

dist:
	bash scripts/build-npm.sh

help:
	go run ./cmd/nerm --help

publish:
	@test -n "$(VERSION)" || (echo "VERSION=x.y.z is required, e.g. make publish VERSION=0.1.1" && exit 1)
	bash scripts/publish-npm.sh $(VERSION) $(GIT)
