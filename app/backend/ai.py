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
    binary: str = "hermes"
    timeout_seconds: int = 120
    model: str = ""
    inference_provider: str = ""
    toolsets: str = ""
    skills: str = ""

    def complete(self, prompt: str) -> str:
        args = [self.binary, "-z", prompt]
        if self.model:
            args.extend(["--model", self.model])
        if self.inference_provider:
            args.extend(["--provider", self.inference_provider])
        if self.toolsets:
            args.extend(["--toolsets", self.toolsets])
        if self.skills:
            args.extend(["--skills", self.skills])
        completed = subprocess.run(
            args,
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


@dataclass
class CodexCLIProvider:
    binary: str = "codex"
    timeout_seconds: int = 180
    model: str = ""
    cwd: str = ""
    sandbox: str = "read-only"
    approval_policy: str = "never"
    ephemeral: bool = True

    def complete(self, prompt: str) -> str:
        args = [self.binary, "exec"]
        if self.cwd:
            args.extend(["-C", self.cwd])
        if self.sandbox:
            args.extend(["--sandbox", self.sandbox])
        if self.approval_policy:
            args.extend(["--ask-for-approval", self.approval_policy])
        if self.ephemeral:
            args.append("--ephemeral")
        if self.model:
            args.extend(["--model", self.model])
        args.append("-")
        completed = subprocess.run(
            args,
            input=prompt,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            message = stderr or f"Codex exited with code {completed.returncode}"
            raise RuntimeError(message)
        return completed.stdout.strip()


@dataclass
class OpenCodeCLIProvider:
    binary: str = "opencode"
    timeout_seconds: int = 180
    model: str = ""

    def complete(self, prompt: str) -> str:
        args = [self.binary, "run"]
        if self.model:
            args.extend(["--model", self.model])
        completed = subprocess.run(
            args,
            input=prompt,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            message = stderr or f"OpenCode exited with code {completed.returncode}"
            raise RuntimeError(message)
        return completed.stdout.strip()
