from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Protocol


class AIProvider(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class FakeAIProvider:
    def complete(self, prompt: str) -> str:
        return f"[fake-ai]\n{prompt}"


@dataclass
class HermesCLIProvider:
    binary: str = "/Users/yang/.local/bin/hermes"
    timeout_seconds: int = 120

    def complete(self, prompt: str) -> str:
        completed = subprocess.run(
            [self.binary, "-z", prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            message = stderr or f"Hermes exited with code {completed.returncode}"
            raise RuntimeError(message)
        return completed.stdout.strip()
