from dataclasses import dataclass
from typing import Literal


TransportKind = Literal["stdio", "streamable-http"]
_VALID_KINDS = {"stdio", "streamable-http"}


@dataclass
class TransportConfig:
    kind: TransportKind
    host: str = "0.0.0.0"
    port: int = 8080

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"Unsupported transport kind: {self.kind}")
        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid transport port: {self.port}")
