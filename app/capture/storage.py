from pathlib import Path
from typing import Protocol
from uuid import uuid4


class ScreenshotStorage(Protocol):
    def save(self, image: bytes) -> str:
        """Persist a screenshot and return a non-public storage reference."""


class LocalScreenshotStorage:
    def __init__(self, output_dir: Path) -> None:
        self._directory = output_dir / "screenshots"

    def save(self, image: bytes) -> str:
        self._directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.png"
        (self._directory / filename).write_bytes(image)
        return f"screenshots/{filename}"
