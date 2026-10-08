package cli

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/nermapi"
	"github.com/sailpoint-se/nerm-cli/internal/profiles"
)

var Version = "0.1.4"

type runtime struct {
	profileName string
	compact     bool
	stdout      io.Writer
	stderr      io.Writer
	store       *profiles.Store
}

func Execute() error {
	return Run(os.Args[1:], os.Stdout, os.Stderr, nil)
}

func Run(args []string, stdout, stderr io.Writer, store *profiles.Store) error {
	rt := &runtime{stdout: stdout, stderr: stderr, store: store}
	cmd := newRoot(rt)
	cmd.SetArgs(args)
	ran, err := cmd.ExecuteC()
	if err != nil && isUsageError(err) {
		_ = ran.Help()
	}
	return err
}

func isUsageError(err error) bool {
	msg := err.Error()
	for _, snippet := range []string{
		"accepts ",
		"requires at least ",
		"required flag",
		"at least one of the flags",
		"if any flags in the group",
		"unknown flag",
		"unknown shorthand flag",
		"unknown command",
		"invalid argument",
		"flag needs an argument",
		"bad flag syntax",
	} {
		if strings.Contains(msg, snippet) {
			return true
		}
	}
	return false
}

func newRoot(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{
		Use:           "nerm",
		Short:         "CLI for SailPoint NERM tenant APIs",
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	cmd.CompletionOptions.DisableDefaultCmd = true
	cmd.PersistentFlags().StringVar(&rt.profileName, "profile", "", "connection profile name")
	cmd.PersistentFlags().BoolVar(&rt.compact, "compact", false, "write compact JSON")
	cmd.PersistentPreRunE = func(cmd *cobra.Command, args []string) error {
		if rt.store == nil {
			rt.store = profiles.NewStore("", nil)
		}
		return nil
	}
	cmd.AddCommand(
		newVersionCmd(rt),
		newConnectionCmd(rt),
		newProfileTypesCmd(rt),
		newProfilesCmd(rt),
		newUsersCmd(rt),
		newUserRolesCmd(rt),
		newUserManagersCmd(rt),
		newUserProfilesCmd(rt),
		newRolesCmd(rt),
		newRoleProfilesCmd(rt),
		newDelegationsCmd(rt),
		newIdentityProofingCmd(rt),
		newAttributesCmd(rt),
		newAttributeOptionsCmd(rt),
		newFormsCmd(rt),
		newFormAttributesCmd(rt),
		newPagesCmd(rt),
		newPageContentsCmd(rt),
		newPageElementsCmd(rt),
		newPageTranslationsCmd(rt),
		newRiskLevelsCmd(rt),
		newRiskScoresCmd(rt),
		newSystemRolesCmd(rt),
		newISCAccountsCmd(rt),
		newWorkflowsCmd(rt),
		newWorkflowActionsCmd(rt),
		newWorkflowActionPerformersCmd(rt),
		newIDProxyCmd(rt),
		newPermissionsCmd(rt),
		newSystemRolePermissionsCmd(rt),
		newLanguagesCmd(rt),
		newAuditCmd(rt),
		newSearchCmd(rt),
		newAPICmd(rt),
		newConfigCmd(rt),
	)
	cmd.SetOut(rt.stdout)
	cmd.SetErr(rt.stderr)
	return cmd
}

func newVersionCmd(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Print CLI version",
		RunE: func(cmd *cobra.Command, args []string) error {
			return writeJSON(rt, map[string]any{"name": "nerm", "version": Version})
		},
	}
}

func (rt *runtime) client() (*client.Client, profiles.Connection, error) {
	conn, err := rt.store.Resolve(rt.profileName)
	if err != nil {
		return nil, conn, err
	}
	return client.New(conn.URL, conn.Token), conn, nil
}

func writeJSON(rt *runtime, payload any) error {
	if asMap, ok := payload.(map[string]any); ok {
		if _, hasErr := asMap["error"]; hasErr {
			if err := encodeJSON(rt, asMap); err != nil {
				return err
			}
			return errors.New(fmt.Sprint(asMap["error"]))
		}
	}
	return encodeJSON(rt, payload)
}

func encodeJSON(rt *runtime, payload any) error {
	enc := json.NewEncoder(rt.stdout)
	if !rt.compact {
		enc.SetIndent("", "  ")
	}
	enc.SetEscapeHTML(false)
	return enc.Encode(payload)
}

func handleAPI(rt *runtime, payload map[string]any, err error) error {
	if err != nil {
		return writeJSON(rt, nermapi.AsErrorJSON(err))
	}
	return writeJSON(rt, payload)
}

func readJSONFlag(body, bodyFile string) (map[string]any, error) {
	raw := strings.TrimSpace(body)
	if bodyFile != "" {
		data, err := os.ReadFile(bodyFile)
		if err != nil {
			return nil, err
		}
		raw = string(data)
	}
	if raw == "" || raw == "-" {
		stat, _ := os.Stdin.Stat()
		if stat != nil && stat.Mode()&os.ModeCharDevice == 0 {
			data, err := io.ReadAll(os.Stdin)
			if err != nil {
				return nil, err
			}
			raw = string(data)
		}
	}
	if strings.TrimSpace(raw) == "" {
		return map[string]any{}, nil
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(raw), &payload); err != nil {
		return nil, fmt.Errorf("invalid JSON body: %w", err)
	}
	return payload, nil
}

func boolPtr(cmd *cobra.Command, name string) *bool {
	if !cmd.Flags().Changed(name) {
		return nil
	}
	value, _ := cmd.Flags().GetBool(name)
	return &value
}

func listFlags(cmd *cobra.Command) {
	cmd.Flags().Int("limit", 100, "page size / retrieval window")
	cmd.Flags().Int("offset", 0, "result offset")
	cmd.Flags().Bool("force-all", false, "continue past the automatic retrieval cap")
	cmd.Flags().String("order", "", "order field")
	cmd.Flags().Bool("metadata", true, "include metadata/total when supported")
}
