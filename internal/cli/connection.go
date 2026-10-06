package cli

import (
	"time"

	"github.com/spf13/cobra"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/nermapi"
	"github.com/sailpoint-se/nerm-cli/internal/profiles"
)

func newConnectionCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "connection", Short: "Manage local NERM connection profiles"}
	cmd.AddCommand(newConnectionAdd(rt), newConnectionList(rt), newConnectionShow(rt), newConnectionUse(rt), newConnectionRemove(rt), newConnectionTest(rt))
	return cmd
}

func newConnectionAdd(rt *runtime) *cobra.Command {
	var url, token, tokenEnv string
	var use bool
	cmd := &cobra.Command{
		Use:   "add NAME",
		Short: "Add or update a connection profile",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			profile, err := rt.store.Add(profiles.AddOptions{
				Name:     args[0],
				URL:      url,
				Token:    token,
				TokenEnv: tokenEnv,
				Use:      use,
			})
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			file, _ := rt.store.Load()
			return writeJSON(rt, profiles.PublicView(profile, file.DefaultProfile == profile.Name))
		},
	}
	cmd.Flags().StringVar(&url, "url", "", "NERM tenant URL")
	cmd.Flags().StringVar(&token, "token", "", "bearer token stored in the OS credential store")
	cmd.Flags().StringVar(&tokenEnv, "token-env", "", "environment variable that holds the bearer token")
	cmd.Flags().BoolVar(&use, "use", false, "make this the default profile")
	_ = cmd.MarkFlagRequired("url")
	return cmd
}

func newConnectionList(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List saved connection profiles",
		RunE: func(cmd *cobra.Command, args []string) error {
			file, err := rt.store.List()
			if err != nil {
				return err
			}
			items := []map[string]any{}
			for name, profile := range file.Profiles {
				profile.Name = name
				items = append(items, profiles.PublicView(profile, file.DefaultProfile == name))
			}
			return writeJSON(rt, map[string]any{"default_profile": file.DefaultProfile, "items": items})
		},
	}
}

func newConnectionShow(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "show NAME",
		Short: "Show one connection profile without secrets",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			profile, err := rt.store.Show(args[0])
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			file, _ := rt.store.Load()
			return writeJSON(rt, profiles.PublicView(profile, file.DefaultProfile == profile.Name))
		},
	}
}

func newConnectionUse(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "use NAME",
		Short: "Set the default connection profile",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := rt.store.Use(args[0]); err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			return writeJSON(rt, map[string]any{"default_profile": args[0]})
		},
	}
}

func newConnectionRemove(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "remove NAME",
		Short: "Remove a connection profile",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := rt.store.Remove(args[0]); err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			return writeJSON(rt, map[string]any{"removed": args[0]})
		},
	}
}

func newConnectionTest(rt *runtime) *cobra.Command {
	return &cobra.Command{
		Use:   "test",
		Short: "Call a harmless profile-types read against the selected profile",
		RunE: func(cmd *cobra.Command, args []string) error {
			c, conn, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			_, err = c.Request("GET", client.ProfileTypes, map[string]any{"limit": 1, "offset": 0}, nil, 15*time.Second)
			if err != nil {
				return handleAPI(rt, nil, err)
			}
			return writeJSON(rt, map[string]any{"ok": true, "profile": conn.Name, "url": conn.URL})
		},
	}
}

func listProfileTypes(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
	c, _, err := rt.client()
	if err != nil {
		return nil, err
	}
	catalog, err := nermapi.FetchCatalog(c, client.ProfileTypes, "profile_types")
	if err != nil {
		return nil, err
	}
	name, _ := cmd.Flags().GetString("name")
	archived := boolPtr(cmd, "archived")
	filtered := []map[string]any{}
	for _, item := range catalog {
		if name != "" && !nermapi.ContainsFold(fmtString(item["name"]), name) {
			continue
		}
		if archived != nil {
			value, _ := item["archived"].(bool)
			if value != *archived {
				continue
			}
		}
		filtered = append(filtered, item)
	}
	order, _ := cmd.Flags().GetString("order")
	if order != "" {
		sortBy(filtered, order)
	}
	limit, _ := cmd.Flags().GetInt("limit")
	offset, _ := cmd.Flags().GetInt("offset")
	return nermapi.SliceCatalog(filtered, limit, offset, boolPtr(cmd, "metadata")), nil
}

func getProfileType(rt *runtime, id string) (map[string]any, error) {
	c, _, err := rt.client()
	if err != nil {
		return nil, err
	}
	catalog, err := nermapi.FetchCatalog(c, client.ProfileTypes, "profile_types")
	if err != nil {
		return nil, err
	}
	item, err := nermapi.FindByID(catalog, id)
	if err != nil {
		return nermapi.AsErrorJSON(err), nil
	}
	return item, nil
}

func fmtString(v any) string {
	if v == nil {
		return ""
	}
	return toString(v)
}
