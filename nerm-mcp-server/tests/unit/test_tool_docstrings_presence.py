import ast
from pathlib import Path


def test_all_nerm_tools_have_docstrings() -> None:
    tools_dir = Path(__file__).resolve().parents[2] / "app" / "nerm" / "tools"
    missing: list[str] = []

    for path in sorted(tools_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("nerm_"):
                if ast.get_docstring(node) is None:
                    missing.append(f"{path.name}:{node.name}")

    assert not missing, f"Missing docstrings for tools: {missing}"
