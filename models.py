from dataclasses import dataclass


@dataclass
class Result:
    id: str
    scenario: str
    repetition: int
    timestamp: str
    duration_ms: float
    status: int | None
    result: str
    error: str
