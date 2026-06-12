from pathlib import Path


def _parse_env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def test_env_and_env_example_keys_are_in_sync() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    env_example_path = repo_root / ".env.example"

    env_keys = _parse_env_keys(env_path)
    env_example_keys = _parse_env_keys(env_example_path)

    missing_in_env = sorted(env_example_keys - env_keys)
    extra_in_env = sorted(env_keys - env_example_keys)

    assert not missing_in_env and not extra_in_env, (
        "Detected .env/.env.example key drift. "
        f"missing_in_env={missing_in_env} extra_in_env={extra_in_env}"
    )
