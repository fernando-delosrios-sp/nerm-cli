from pathlib import Path

from nerm.client import endpoints
from nerm.tools.registry import NERM_TOOLS


def test_tool_endpoint_matrix_covers_all_registered_tools() -> None:
    matrix = Path(__file__).resolve().parents[2] / "docs" / "TOOL_ENDPOINT_MATRIX.md"
    content = matrix.read_text(encoding="utf-8")
    documented_tools = {
        line.split("`")[1]
        for line in content.splitlines()
        if line.startswith("| `nerm_")
    }
    assert documented_tools == set(NERM_TOOLS.keys())


def test_tool_endpoint_matrix_uses_known_endpoint_constants() -> None:
    matrix = Path(__file__).resolve().parents[2] / "docs" / "TOOL_ENDPOINT_MATRIX.md"
    content = matrix.read_text(encoding="utf-8")
    known_endpoint_values = {
        value
        for name, value in vars(endpoints).items()
        if name.isupper() and isinstance(value, str)
    }

    def _normalize_endpoint(raw: str) -> str:
        endpoint = raw.strip().replace("`", "")
        if " (" in endpoint:
            endpoint = endpoint.split(" (", 1)[0].strip()
        if endpoint.endswith("/:id"):
            endpoint = endpoint[: -len("/:id")]
        return endpoint

    for line in content.splitlines():
        if not line.startswith("| `nerm_"):
            continue
        cols = [col.strip() for col in line.split("|")]
        # | tool | method | endpoint | smoke |
        endpoint_col = cols[3]
        endpoint_unwrapped = endpoint_col.strip("`")
        if endpoint_unwrapped in {"N/A", "local JWT decode", "in-process"}:
            continue
        normalized = _normalize_endpoint(endpoint_unwrapped)
        assert normalized in known_endpoint_values, f"Unknown endpoint in matrix: {endpoint_unwrapped}"


def test_tool_endpoint_matrix_uses_valid_smoke_coverage_values() -> None:
    matrix = Path(__file__).resolve().parents[2] / "docs" / "TOOL_ENDPOINT_MATRIX.md"
    content = matrix.read_text(encoding="utf-8")
    allowed = {"yes", "no", "guarded"}

    for line in content.splitlines():
        if not line.startswith("| `nerm_"):
            continue
        cols = [col.strip() for col in line.split("|")]
        smoke = cols[4].replace("`", "").strip().lower()
        assert smoke in allowed, f"Invalid smoke coverage value '{smoke}' in line: {line}"
