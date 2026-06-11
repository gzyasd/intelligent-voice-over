"""LALAL.AI separation provider adapter.

Multi-step workflow: upload → split → check → download → cleanup.
Implements SeparationAdapter protocol for the pipeline.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from ivo.model_services.adapters.base import ConnectionValidationResult


class LalalaiProvider:
    """Provider adapter for LALAL.AI audio separation API."""

    BASE_URL = "https://www.lalal.ai"
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
        self.provider_id = "lalalai"
        self.stage = "separation"
        self.protocol = "lalalai_separation"
        self._api_key = api_key
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by checking account/balance info."""
        try:
            response = httpx.request(
                "GET",
                f"{self.BASE_URL}/api/v1/check/",
                headers={"X-License-Key": self._api_key},
                json={"task_ids": []},
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
                    error_message="Invalid license key",
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

    def to_pipeline_adapter(self) -> _LalalaiSeparationAdapter:
        """Return a pipeline-compatible separation adapter."""
        return _LalalaiSeparationAdapter(self)

    # -- Internal API methods --

    def _upload_file(self, file_path: Path) -> str:
        """Upload audio file and return source_id."""
        filename = file_path.name
        # RFC 5987 encoded filename for non-ASCII support
        ascii_name = filename.encode("ascii", "replace").decode("ascii")
        with open(file_path, "rb") as f:
            response = httpx.post(
                f"{self.BASE_URL}/api/v1/upload/",
                headers={
                    "X-License-Key": self._api_key,
                    "Content-Disposition": f'attachment; filename="{ascii_name}"',
                },
                content=f.read(),
                timeout=120.0,
            )
        response.raise_for_status()
        data = response.json()
        return str(data["id"])

    def _submit_split(self, source_id: str) -> str:
        """Submit separation task and return task_id."""
        response = httpx.post(
            f"{self.BASE_URL}/api/v1/split/stem_separator/",
            headers={
                "X-License-Key": self._api_key,
                "Content-Type": "application/json",
            },
            json={
                "source_id": source_id,
                "presets": {
                    "stem": "vocals",
                    "extraction_level": "deep_extraction",
                    "splitter": "auto",
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["task_id"])

    def _check_status(self, task_id: str) -> dict[str, Any]:
        """Check task status. Returns task result dict."""
        response = httpx.post(
            f"{self.BASE_URL}/api/v1/check/",
            headers={
                "X-License-Key": self._api_key,
                "Content-Type": "application/json",
            },
            json={"task_ids": [task_id]},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {}).get(task_id, {})
        return result  # type: ignore[no-any-return]

    def _poll_until_done(self, task_id: str) -> dict[str, Any]:
        """Poll task until completed."""
        interval = self.POLL_INTERVAL_INITIAL
        elapsed = 0.0
        while elapsed < self.POLL_TIMEOUT:
            result = self._check_status(task_id)
            status = result.get("status", "unknown")
            if status == "success":
                return result
            if status == "cancelled":
                raise RuntimeError(f"LALAL.AI task {task_id} was cancelled")
            time.sleep(interval)
            elapsed += interval
            interval = min(interval * self.POLL_BACKOFF_FACTOR, self.POLL_INTERVAL_MAX)
        raise TimeoutError(f"LALAL.AI task {task_id} timed out after {self.POLL_TIMEOUT}s")

    def _download_file(self, url: str, output_path: Path) -> None:
        """Download file from URL to output_path."""
        with httpx.stream("GET", url, timeout=120.0) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    def _delete_source(self, source_id: str) -> None:
        """Cleanup uploaded source file."""
        try:
            httpx.post(
                f"{self.BASE_URL}/api/v1/delete/",
                headers={
                    "X-License-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={"source_id": source_id},
                timeout=10.0,
            )
        except httpx.HTTPError:
            pass  # Cleanup is best-effort


class _LalalaiSeparationAdapter:
    """Implements SeparationAdapter protocol for LALAL.AI."""

    def __init__(self, provider: LalalaiProvider) -> None:
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
        source_id = self._provider._upload_file(input_path)

        try:
            # Step 2: Submit split
            task_id = self._provider._submit_split(source_id)

            # Step 3: Poll until done
            result = self._provider._poll_until_done(task_id)

            # Step 4: Download results - match by label, not index
            tracks = result.get("result", {}).get("tracks", [])
            for track in tracks:
                label = track.get("label", "").lower()
                url = track.get("url", "")
                if label == "vocals":
                    self._provider._download_file(url, vocals_out)
                elif label in ("music", "instrumental", "background"):
                    self._provider._download_file(url, background_out)
        finally:
            # Step 5: Cleanup
            self._provider._delete_source(source_id)

        return {
            "vocals_path": str(vocals_out),
            "background_path": str(background_out),
        }
