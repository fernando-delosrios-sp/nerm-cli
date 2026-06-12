from nerm.services.pagination import (
    apply_pagination_circuit_breaker,
    collect_paginated_items,
    extract_total_count,
    unique_item_count,
)


def test_pagination_circuit_breaker_default() -> None:
    assert apply_pagination_circuit_breaker(50) is True
    assert apply_pagination_circuit_breaker(51) is False
    assert apply_pagination_circuit_breaker(200, force_all=True) is True


def test_extract_total_count_supports_nested_metadata_shapes() -> None:
    assert extract_total_count({"total": 42}) == 42
    assert extract_total_count({"metadata": {"total": 43}}) == 43
    assert extract_total_count({"meta": {"total_count": "44"}}) == 44
    assert extract_total_count({"pagination": {"count": 45}}) == 45


def test_unique_item_count_dedupes_ids() -> None:
    items = [{"id": "a"}, {"id": "a"}, {"id": "b"}, {"name": "no-id"}]
    assert unique_item_count(items) == 3


def test_collect_paginated_items_clamps_to_metadata_total() -> None:
    pages = [
        {"metadata": {"total": 41}, "items": [{"id": str(i)} for i in range(43)]},
    ]
    calls = {"n": 0}

    def fetch_page(offset: int, limit: int, pages: int, collected: int) -> object:  # noqa: ANN001
        del offset, limit, pages, collected
        current = pages_[calls["n"]]
        calls["n"] += 1
        return current

    def parse_items(payload: object) -> list[dict]:
        if isinstance(payload, dict):
            return payload.get("items", [])
        return []

    pages_ = pages
    items, fetched_pages, pagination_limited, total_count, confirmation = collect_paginated_items(
        bounded_limit=100,
        bounded_offset=0,
        force_all=False,
        fetch_page=fetch_page,
        parse_page_items=parse_items,
    )
    assert confirmation is None
    assert total_count == 41
    assert fetched_pages == 1
    assert pagination_limited is False
    assert len(items) == 41


def test_collect_paginated_items_derives_total_when_metadata_missing_and_window_full() -> None:
    pages = [
        {"items": [{"id": f"a-{i}"} for i in range(100)]},
        {"items": [{"id": "a-100"}]},
    ]
    calls = {"n": 0}

    def fetch_page(offset: int, limit: int, pages_fetched: int, collected: int) -> object:  # noqa: ANN001
        del offset, limit, pages_fetched, collected
        current = pages[calls["n"]] if calls["n"] < len(pages) else {"items": []}
        calls["n"] += 1
        return current

    def parse_items(payload: object) -> list[dict]:
        if isinstance(payload, dict):
            return payload.get("items", [])
        return []

    items, fetched_pages, pagination_limited, total_count, confirmation = collect_paginated_items(
        bounded_limit=100,
        bounded_offset=0,
        force_all=False,
        fetch_page=fetch_page,
        parse_page_items=parse_items,
    )
    assert confirmation is None
    assert len(items) == 100
    assert total_count == 101
    assert fetched_pages == 2
    assert pagination_limited is False
