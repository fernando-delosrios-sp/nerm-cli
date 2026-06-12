from nerm.url_utils import normalize_base_url


def test_normalize_base_url_preserves_query_and_fragment() -> None:
    normalized = normalize_base_url("https://tenant.example.com/?a=1#frag", "/api")
    assert normalized == "https://tenant.example.com/api?a=1#frag"


def test_normalize_base_url_trims_trailing_slash_when_path_present() -> None:
    normalized = normalize_base_url("https://tenant.example.com/custom/path/", "/api")
    assert normalized == "https://tenant.example.com/custom/path"


def test_normalize_base_url_keeps_non_url_input_path_style() -> None:
    normalized = normalize_base_url("tenant.example.com/api/", "/api")
    assert normalized == "tenant.example.com/api"
