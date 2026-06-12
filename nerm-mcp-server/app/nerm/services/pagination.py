from collections.abc import Callable
from typing import TypeVar

PAGINATION_CIRCUIT_BREAKER_MAX_RECORDS = 5000
PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE = 100
PAGINATION_CIRCUIT_BREAKER_MAX_PAGES = PAGINATION_CIRCUIT_BREAKER_MAX_RECORDS // PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE
T = TypeVar("T")


def apply_pagination_circuit_breaker(pages_requested: int, force_all: bool = False) -> bool:
    if force_all:
        return True
    return pages_requested <= PAGINATION_CIRCUIT_BREAKER_MAX_PAGES


def extract_total_count(payload: object) -> int | None:
    def _coerce_non_negative_int(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, str):
            text = value.strip()
            if text.isdigit():
                return int(text)
        return None

    if not isinstance(payload, dict):
        return None
    direct = _coerce_non_negative_int(payload.get("total"))
    if direct is not None:
        return direct
    for key in ("total_count", "count"):
        value = _coerce_non_negative_int(payload.get(key))
        if value is not None:
            return value
    for container_key in ("metadata", "meta", "pagination"):
        container = payload.get(container_key)
        if not isinstance(container, dict):
            continue
        for key in ("total", "total_count", "count"):
            value = _coerce_non_negative_int(container.get(key))
            if value is not None:
                return value
    return None


def unique_item_count(items: list[object]) -> int:
    seen_ids: set[str] = set()
    without_id = 0
    for item in items:
        if isinstance(item, dict) and item.get("id") is not None:
            seen_ids.add(str(item.get("id")))
        else:
            without_id += 1
    return len(seen_ids) + without_id


def confirm_large_result_set(total: int | None, force_all: bool) -> dict | None:
    if force_all or total is None or total <= PAGINATION_CIRCUIT_BREAKER_MAX_RECORDS:
        return None
    return {
        "error": "confirmation_required",
        "message": (
            f"This query matches {total} records, which exceeds the automatic retrieval cap of "
            f"{PAGINATION_CIRCUIT_BREAKER_MAX_RECORDS}. Ask the user if they want all data."
        ),
        "total": total,
        "guidance": {
            "next_step": "If user confirms, retry with force_all=true to retrieve all records.",
        },
    }


def collect_paginated_items(
    *,
    bounded_limit: int,
    bounded_offset: int,
    force_all: bool,
    fetch_page: Callable[[int, int, int, int], object],
    parse_page_items: Callable[[object], list[T]],
) -> tuple[list[T], int, bool, int | None, dict | None]:
    collected: list[T] = []
    current_offset = bounded_offset
    pages = 0
    expected_window_total: int | None = None
    total_count: int | None = None

    while len(collected) < bounded_limit and apply_pagination_circuit_breaker(pages + 1, force_all=force_all):
        if expected_window_total is not None and current_offset >= (bounded_offset + expected_window_total):
            break
        page_limit = min(PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE, bounded_limit - len(collected))
        payload = fetch_page(current_offset, page_limit, pages, len(collected))
        if pages == 0:
            total_count = extract_total_count(payload)
            if total_count is not None:
                remaining = max(total_count - bounded_offset, 0)
                expected_window_total = min(bounded_limit, remaining)
            confirmation_needed = confirm_large_result_set(total_count, force_all=force_all)
            if confirmation_needed:
                return [], pages, False, total_count, confirmation_needed

        page_typed = parse_page_items(payload)
        collected.extend(page_typed)
        pages += 1

        if len(page_typed) == 0:
            break
        current_offset += len(page_typed)
        if expected_window_total is not None and len(collected) >= expected_window_total:
            break
        if expected_window_total is None and len(page_typed) < PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE:
            break

    # If metadata total is missing and we exactly filled the requested window from offset 0,
    # continue paging in count-only mode to derive a reliable total.
    if (
        total_count is None
        and not force_all
        and bounded_offset == 0
        and len(collected) == bounded_limit
        and bounded_limit > 0
    ):
        counted_records = len(collected)
        probe_offset = current_offset
        probe_pages = pages
        while apply_pagination_circuit_breaker(probe_pages + 1, force_all=force_all):
            payload = fetch_page(
                probe_offset,
                PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE,
                probe_pages,
                counted_records,
            )
            page_typed = parse_page_items(payload)
            probe_pages += 1
            if len(page_typed) == 0:
                break
            counted_records += len(page_typed)
            probe_offset += len(page_typed)
            if len(page_typed) < PAGINATION_CIRCUIT_BREAKER_PAGE_SIZE:
                break
        total_count = counted_records
        pages = probe_pages

    effective_limit = bounded_limit
    if expected_window_total is not None:
        effective_limit = min(effective_limit, expected_window_total)
    returned_items = collected[:effective_limit]
    pagination_limited = (
        not force_all and pages >= PAGINATION_CIRCUIT_BREAKER_MAX_PAGES and len(returned_items) < effective_limit
    )
    return returned_items, pages, pagination_limited, total_count, None
