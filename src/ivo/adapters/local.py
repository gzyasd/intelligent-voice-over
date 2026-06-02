from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field

from ivo.adapters.base import AdapterContext, AdapterError, AdapterResult, MockStageAdapter

CommandRunner = Callable[[list[str]], None]


class LocalCommandProfile(BaseModel):
    id: str
    stage: str
    command: list[str]
    output_json_path: str
    extra: dict[str, Any] = Field(default_factory=dict)


class LocalCommandAdapter:
    def __init__(
        self,
        profile: LocalCommandProfile,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.profile = profile
        self.stage = profile.stage
        self.provider = profile.id
        self.runner = runner
        self._environment = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)

    def validate_config(self) -> None:
        if not self.profile.command:
            raise ValueError("local command cannot be empty")

    def run(self, context: AdapterContext) -> AdapterResult:
        values = context.template_values()
        values.update(self.profile.extra)
        values["output_json_path"] = self._render_string(self.profile.output_json_path, values)
        command = [self._render_string(part, values) for part in self.profile.command]
        output_path = Path(str(values["output_json_path"]))

        try:
            if self.runner is None:
                subprocess.run(command, check=True)
            else:
                self.runner(command)
            if not output_path.is_file():
                return self._error(f"output JSON not found: {output_path}")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return self._error("output JSON must be an object")
            return AdapterResult(
                stage=self.stage,
                provider=self.provider,
                ok=True,
                payload=payload,
            )
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            return self._error(str(exc))

    def _render_string(self, template: str, variables: dict[str, Any]) -> str:
        return self._environment.from_string(template).render(**variables)

    def _error(self, message: str) -> AdapterResult:
        return AdapterResult(
            stage=self.stage,
            provider=self.provider,
            ok=False,
            error=AdapterError(
                provider=self.provider,
                stage=self.stage,
                message=message,
                retryable=False,
            ),
        )

__all__ = ["LocalCommandAdapter", "LocalCommandProfile", "MockStageAdapter"]
