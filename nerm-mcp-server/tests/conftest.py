from pathlib import Path

import pytest
from dotenv import load_dotenv

from nerm.config import Settings


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)


@pytest.fixture
def settings() -> Settings:
    return Settings()
