from dataclasses import dataclass


@dataclass
class NermApiError(Exception):
    status: int
    body: str

    def as_error_json(self) -> dict[str, object]:
        return {"error": "nerm_api_error", "status": self.status, "body": self.body}
