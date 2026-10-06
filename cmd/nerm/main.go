package main

import (
	"os"

	"github.com/sailpoint-se/nerm-cli/internal/cli"
)

func main() {
	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
