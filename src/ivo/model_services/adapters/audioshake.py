"""AudioShake separation provider adapter.

Async workflow: upload file → create task → poll → download results.
Implements SeparationAdapter protocol for the pipeline.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from ivo.model_services.adapters.base import ConnectionValidationResult


class AudioShakeProvider:
    """Provider adapter for AudioShake audio separation API."""

    BASE_URL = "https://api.audioshake.ai"
    POLL_INTERVAL_INITIAL = 3.0
    POLL_INTERVAL_MAX = 30.0
    POLL_BACKOFF_FACTOR = 1.5
    POLL_TIMEOUT = 600.0  # 10 minutes

    def __init__(
        self,
        *,
        api_key: str,
        config_id: str = "",
    ) -> None:
        self.provider_id = "audioshake"
        self.stage = "separation"
        self.protocol = "audioshake_separation"
        self._api_key = api_key
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by listing tasks (skip=0, take=1)."""
        try:
            response = httpx.get(
                f"{self.BASE_URL}/tasks",
                params={"skip": "0", "take": "1"},
                headers={"x-api-key": self._api_key},
                timeout=10.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                )
            if response.status_code in (401, 403):
                return ConnectionValidationResult(
                    ok=False,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    error_message="Invalid API key",
                    error_code="AUTH_FAILED",
                )
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=f"HTTP {response.status_code}",
                error_code="CONNECTION_ERROR",
            )
        except httpx.HTTPError as exc:
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=str(exc)[:200],
                error_code="CONNECTION_ERROR",
            )

    def to_pipeline_adapter(self) -> _AudioShakeSeparationAdapter:
        """Return a pipeline-compatible separation adapter."""
        return _AudioShakeSeparationAdapter(self)

    # -- Internal API methods --

    def _upload_asset(self, file_path: Path) -> str:
        """Upload audio file and return asset_id."""
        with open(file_path, "rb") as f:
            response = httpx.post(
                f"{self.BASE_URL}/assets",
                headers={"x-api-key": self._api_key},
                files={"file": (file_path.name, f, "audio/wav")},
                timeout=120.0,
            )
        response.raise_for_status()
        data = response.json()
        return str(data["id"])

    def _create_task(self, asset_id: str) -> str:
        """Create separation task and return task_id."""
        response = httpx.post(
            f"{self.BASE_URL}/tasks",
            headers={
                "x-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            json={
                "assetId": asset_id,
                "targets": [
                    {"model": "vocals", "formats": ["wav"]},
                    {"model": "instrumental", "formats": ["wav"]},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["id"])

    def _check_status(self, task_id: str) -> tuple[str, dict[str, Any]]:
        """Check task status. Returns (status, response_data)."""
        response = httpx.get(
            f"{self.BASE_URL}/tasks/{task_id}",
            headers={"x-api-key": self._api_key},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("status", "unknown")), data

    def _download_file(self, url: str, output_path: Path) -> None:
        """Download file from URL to output_path."""
        with httpx.stream("GET", url, timeout=120.0) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    def _poll_until_done(self, task_id: str) -> dict[str, Any]:
        """Poll task until completed or failed."""
        interval = self.POLL_INTERVAL_INITIAL
        elapsed = 0.0
        while elapsed < self.POLL_TIMEOUT:
            status, data = self._check_status(task_id)
            if status == "completed":
                return data
            if status == "failed":
                raise RuntimeError(f"AudioShake task {task_id} failed")
            time.sleep(interval)
            elapsed += interval
            interval = min(interval * self.POLL_BACKOFF_FACTOR, self.POLL_INTERVAL_MAX)
        raise TimeoutError(f"AudioShake task {task_id} timed out after {self.POLL_TIMEOUT}s")


class _AudioShakeSeparationAdapter:
    """Implements SeparationAdapter protocol for AudioShake."""

    def __init__(self, provider: AudioShakeProvider) -> None:
        self._provider = provider

    def separate(
        self,
        input_audio: Any,
        *,
        vocals_path: Any,
        background_path: Any,
    ) -> Any:
        """Separate audio into vocals and background tracks."""
        input_path = Path(str(input_audio))
        vocals_out = Path(str(vocals_path))
        background_out = Path(str(background_path))

        if not input_path.is_file():
            raise FileNotFoundError(input_path)

        # Step 1: Upload
        asset_id = self._provider._upload_asset(input_path)

        # Step 2: Create task
        task_id = self._provider._create_task(asset_id)

        # Step 3: Poll until done
        result_data = self._provider._poll_until_done(task_id)

        # Step 4: Download results
        targets = result_data.get("targets", [])
        vocals_url: str | None = None
        instrumental_url: str | None = None

        for target in targets:
            model = target.get("model", "")
            outputs = target.get("output", [])
            if outputs:
                url = outputs[0].get("link", "")
                if model == "vocals":
                    vocals_url = url
                elif model == "instrumental":
                    instrumental_url = url

        if vocals_url:
            self._provider._download_file(vocals_url, vocals_out)
        if instrumental_url:
            self._provider._download_file(instrumental_url, background_out)

        return {
            "vocals_path": str(vocals_out),
            "background_path": str(background_out),
        }
