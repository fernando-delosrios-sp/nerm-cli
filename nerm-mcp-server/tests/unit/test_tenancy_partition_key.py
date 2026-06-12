from nerm.tenancy import tenant_partition_key


def test_partition_key_changes_by_tenant() -> None:
    key1 = tenant_partition_key("https://a", "token-a")
    key2 = tenant_partition_key("https://b", "token-b")
    assert key1 != key2
