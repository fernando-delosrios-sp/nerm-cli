package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

type flagSpec struct {
	name string
	api  string
	help string
	kind string // "string" (default) or "bool"
}

type op struct {
	Use    string
	Short  string
	Method string
	Path   string
	Args   []string
	Body   bool
	File   bool
	Query  []flagSpec
}

func (o op) usage() string {
	if len(o.Args) == 0 {
		return o.Use
	}
	return o.Use + " " + strings.Join(o.Args, " ")
}

func addOps(parent *cobra.Command, rt *runtime, ops []op) {
	for _, item := range ops {
		parent.AddCommand(newOp(rt, item))
	}
}

func newOp(rt *runtime, item op) *cobra.Command {
	var body, bodyFile, filePath string
	cmd := &cobra.Command{
		Use:   item.usage(),
		Short: item.Short,
		Args:  cobra.ExactArgs(len(item.Args)),
		RunE: func(cmd *cobra.Command, args []string) error {
			path := item.Path
			if strings.Contains(path, "%") {
				vals := make([]any, len(args))
				for i, arg := range args {
					vals[i] = arg
				}
				path = fmt.Sprintf(path, vals...)
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			query := queryFlags(cmd, item.Query)
			if item.File {
				data, err := os.ReadFile(filePath)
				if err != nil {
					return err
				}
				result, err := c.RequestFile(item.Method, path, query, "file", filepath.Base(filePath), data, 120*time.Second)
				return writeResult(rt, result, err)
			}
			var reqBody any
			if item.Body {
				payload, err := readJSONFlag(body, bodyFile)
				if err != nil {
					return err
				}
				reqBody = payload
			}
			result, err := c.Request(item.Method, path, query, reqBody, 30*time.Second)
			return writeResult(rt, result, err)
		},
	}
	if item.Body {
		cmd.Flags().StringVar(&body, "body", "", "JSON body, sent as given")
		cmd.Flags().StringVar(&bodyFile, "body-file", "", "JSON body file, sent as given")
	}
	if item.File {
		cmd.Flags().StringVar(&filePath, "file", "", "file to upload as the form field file")
		_ = cmd.MarkFlagRequired("file")
	}
	registerFlags(cmd, item.Query)
	return cmd
}

func registerFlags(cmd *cobra.Command, flags []flagSpec) {
	for _, flag := range flags {
		switch flag.kind {
		case "bool":
			cmd.Flags().Bool(flag.name, false, flag.help)
		default:
			cmd.Flags().String(flag.name, "", flag.help)
		}
	}
}

func collectionQuery(cmd *cobra.Command, flags []flagSpec) map[string]any {
	out := queryFlags(cmd, flags)
	if out == nil {
		out = map[string]any{}
	}
	if order, err := cmd.Flags().GetString("order"); err == nil && order != "" {
		out["order"] = order
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func queryFlags(cmd *cobra.Command, flags []flagSpec) map[string]any {
	out := map[string]any{}
	for _, flag := range flags {
		switch flag.kind {
		case "bool":
			if cmd.Flags().Changed(flag.name) {
				value, _ := cmd.Flags().GetBool(flag.name)
				out[flag.api] = value
			}
		default:
			value, _ := cmd.Flags().GetString(flag.name)
			if value != "" {
				out[flag.api] = value
			}
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func writeResult(rt *runtime, result any, err error) error {
	if err != nil {
		return handleAPI(rt, nil, err)
	}
	if asMap, ok := result.(map[string]any); ok {
		return writeJSON(rt, asMap)
	}
	return writeJSON(rt, map[string]any{"result": result})
}

func rawGet(rt *runtime, path string, query map[string]any) error {
	c, _, err := rt.client()
	if err != nil {
		return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
	}
	result, err := c.Request("GET", path, query, nil, 30*time.Second)
	return writeResult(rt, result, err)
}

func newCollection(rt *runtime, use, short, path, key string, withGet bool, filters []flagSpec, writes []op) *cobra.Command {
	cmd := &cobra.Command{Use: use, Short: short}
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List " + use,
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, path, key, "", collectionQuery(cmd, filters), nil)
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(listCmd)
	registerFlags(listCmd, filters)
	cmd.AddCommand(listCmd)
	if withGet {
		cmd.AddCommand(&cobra.Command{
			Use:   "get ID",
			Short: "Get one " + use + " record",
			Args:  cobra.ExactArgs(1),
			RunE: func(cmd *cobra.Command, args []string) error {
				payload, err := getPath(rt, path, args[0])
				return handleAPI(rt, payload, err)
			},
		})
	}
	addOps(cmd, rt, writes)
	return cmd
}
