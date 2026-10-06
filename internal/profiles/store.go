package profiles

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/zalando/go-keyring"

	"github.com/sailpoint-se/nerm-cli/internal/urlutil"
)

const (
	ServiceName = "nerm-cli"
	TokenKeyring = "keyring"
	TokenEnv     = "env"
)

var (
	ErrNotFound     = errors.New("profile not found")
	ErrKeyring      = errors.New("secure credential store unavailable")
	ErrMissingToken = errors.New("profile token is missing")
)

type Keyring interface {
	Set(service, user, password string) error
	Get(service, user string) (string, error)
	Delete(service, user string) error
}

type OSKeyring struct{}

func (OSKeyring) Set(service, user, password string) error {
	return keyring.Set(service, user, password)
}

func (OSKeyring) Get(service, user string) (string, error) {
	return keyring.Get(service, user)
}

func (OSKeyring) Delete(service, user string) error {
	return keyring.Delete(service, user)
}

type Profile struct {
	Name        string `json:"name,omitempty"`
	URL         string `json:"url"`
	TokenSource string `json:"token_source"`
	TokenEnv    string `json:"token_env,omitempty"`
}

type File struct {
	DefaultProfile string             `json:"default_profile"`
	Profiles       map[string]Profile `json:"profiles"`
}

type Store struct {
	Dir     string
	Keyring Keyring
}

type Connection struct {
	Name  string
	URL   string
	Token string
}

func DefaultDir() string {
	if override := strings.TrimSpace(os.Getenv("NERM_CONFIG_DIR")); override != "" {
		return override
	}
	base, err := os.UserConfigDir()
	if err != nil || strings.TrimSpace(base) == "" {
		home, _ := os.UserHomeDir()
		base = filepath.Join(home, ".config")
	}
	return filepath.Join(base, "nerm-cli")
}

func NewStore(dir string, kr Keyring) *Store {
	if kr == nil {
		kr = OSKeyring{}
	}
	if dir == "" {
		dir = DefaultDir()
	}
	return &Store{Dir: dir, Keyring: kr}
}

func (s *Store) ConfigPath() string {
	return filepath.Join(s.Dir, "config.json")
}

func (s *Store) Load() (File, error) {
	data, err := os.ReadFile(s.ConfigPath())
	if errors.Is(err, os.ErrNotExist) {
		return File{Profiles: map[string]Profile{}}, nil
	}
	if err != nil {
		return File{}, err
	}
	var file File
	if err := json.Unmarshal(data, &file); err != nil {
		return File{}, err
	}
	if file.Profiles == nil {
		file.Profiles = map[string]Profile{}
	}
	return file, nil
}

func (s *Store) Save(file File) error {
	if err := os.MkdirAll(s.Dir, 0o700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.ConfigPath(), append(data, '\n'), 0o600)
}

type AddOptions struct {
	Name     string
	URL      string
	Token    string
	TokenEnv string
	Use      bool
}

func (s *Store) Add(opts AddOptions) (Profile, error) {
	name := strings.TrimSpace(opts.Name)
	if name == "" {
		return Profile{}, errors.New("profile name is required")
	}
	if strings.TrimSpace(opts.URL) == "" {
		return Profile{}, errors.New("profile URL is required")
	}
	file, err := s.Load()
	if err != nil {
		return Profile{}, err
	}
	profile := Profile{
		URL: urlutil.EnsureAPISuffix(opts.URL),
	}
	if strings.TrimSpace(opts.TokenEnv) != "" {
		profile.TokenSource = TokenEnv
		profile.TokenEnv = strings.TrimSpace(opts.TokenEnv)
	} else {
		if strings.TrimSpace(opts.Token) == "" {
			return Profile{}, errors.New("provide --token or --token-env")
		}
		if err := s.Keyring.Set(ServiceName, name, strings.TrimSpace(opts.Token)); err != nil {
			return Profile{}, fmt.Errorf("%w: %v; use --token-env instead", ErrKeyring, err)
		}
		profile.TokenSource = TokenKeyring
	}
	file.Profiles[name] = profile
	if opts.Use || file.DefaultProfile == "" {
		file.DefaultProfile = name
	}
	if err := s.Save(file); err != nil {
		return Profile{}, err
	}
	profile.Name = name
	return profile, nil
}

func (s *Store) List() (File, error) {
	return s.Load()
}

func (s *Store) Show(name string) (Profile, error) {
	file, err := s.Load()
	if err != nil {
		return Profile{}, err
	}
	profile, ok := file.Profiles[name]
	if !ok {
		return Profile{}, fmt.Errorf("%w: %s", ErrNotFound, name)
	}
	profile.Name = name
	return profile, nil
}

func (s *Store) Use(name string) error {
	file, err := s.Load()
	if err != nil {
		return err
	}
	if _, ok := file.Profiles[name]; !ok {
		return fmt.Errorf("%w: %s", ErrNotFound, name)
	}
	file.DefaultProfile = name
	return s.Save(file)
}

func (s *Store) Remove(name string) error {
	file, err := s.Load()
	if err != nil {
		return err
	}
	if _, ok := file.Profiles[name]; !ok {
		return fmt.Errorf("%w: %s", ErrNotFound, name)
	}
	delete(file.Profiles, name)
	if file.DefaultProfile == name {
		file.DefaultProfile = ""
		for candidate := range file.Profiles {
			file.DefaultProfile = candidate
			break
		}
	}
	_ = s.Keyring.Delete(ServiceName, name)
	return s.Save(file)
}

func (s *Store) Resolve(name string) (Connection, error) {
	file, err := s.Load()
	if err != nil {
		return Connection{}, err
	}
	if strings.TrimSpace(name) == "" {
		name = file.DefaultProfile
	}
	if name == "" {
		return Connection{}, errors.New("no connection profile selected; run nerm connection add")
	}
	profile, ok := file.Profiles[name]
	if !ok {
		return Connection{}, fmt.Errorf("%w: %s", ErrNotFound, name)
	}
	token, err := s.tokenFor(profile, name)
	if err != nil {
		return Connection{}, err
	}
	return Connection{Name: name, URL: profile.URL, Token: token}, nil
}

func (s *Store) tokenFor(profile Profile, name string) (string, error) {
	switch profile.TokenSource {
	case TokenEnv:
		value := strings.TrimSpace(os.Getenv(profile.TokenEnv))
		if value == "" {
			return "", fmt.Errorf("%w: environment variable %s is empty", ErrMissingToken, profile.TokenEnv)
		}
		return value, nil
	default:
		value, err := s.Keyring.Get(ServiceName, name)
		if err != nil {
			return "", fmt.Errorf("%w: %v", ErrMissingToken, err)
		}
		if strings.TrimSpace(value) == "" {
			return "", ErrMissingToken
		}
		return value, nil
	}
}

func PublicView(profile Profile, isDefault bool) map[string]any {
	out := map[string]any{
		"name":         profile.Name,
		"url":          profile.URL,
		"token_source": profile.TokenSource,
		"default":      isDefault,
	}
	if profile.TokenEnv != "" {
		out["token_env"] = profile.TokenEnv
	}
	return out
}
