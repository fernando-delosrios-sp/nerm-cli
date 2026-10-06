package profiles

import "sync"

type MemoryKeyring struct {
	mu   sync.Mutex
	data map[string]string
}

func NewMemoryKeyring() *MemoryKeyring {
	return &MemoryKeyring{data: map[string]string{}}
}

func (m *MemoryKeyring) key(service, user string) string {
	return service + "/" + user
}

func (m *MemoryKeyring) Set(service, user, password string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.data[m.key(service, user)] = password
	return nil
}

func (m *MemoryKeyring) Get(service, user string) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	value, ok := m.data[m.key(service, user)]
	if !ok {
		return "", ErrMissingToken
	}
	return value, nil
}

func (m *MemoryKeyring) Delete(service, user string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.data, m.key(service, user))
	return nil
}
