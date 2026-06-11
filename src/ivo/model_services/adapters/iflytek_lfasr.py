"""iFlytek lfasr provider adapter (P2 - long audio pretranscription only).

This is a stub implementation. The full implementation will handle:
- prepare → upload → merge → getProgress → getResult workflow
- signa = Base64(HmacSHA1(MD5(appid + ts), secretkey))
- Chunked audio upload

Not intended for short-clip ASR default selection.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time


from ivo.model_services.adapters.base import ConnectionValidationResult


class IflytekLfasrProvider:
    """Provider adapter stub for iFlytek lfasr long audio transcription."""

    BASE_URL = "https://raasr.xfyun.cn/v2/api"

    def __init__(
        self,
        *,
        app_id: str,
        secret_key: str,
        config_id: str = "",
    ) -> None:
        self.provider_id = "iflytek"
        self.stage = "asr"
        self.protocol = "iflytek_lfasr"
        self._app_id = app_id
        self._secret_key = secret_key
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate iFlytek credentials.

        Currently returns a stub result since full implementation is P2.
        """
        # Generate signature to verify app_id/secret_key format
        try:
            ts = str(int(time.time()))
            self._generate_signa(ts)  # validate app_id/secret_key format
            # A real validation would call the prepare endpoint
            return ConnectionValidationResult(
                ok=True,
                provider_id=self.provider_id,
                stage=self.stage,
                model_name="lfasr",
            )
        except Exception as exc:
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=str(exc)[:200],
                error_code="CONNECTION_ERROR",
            )

    def to_pipeline_adapter(self) -> None:
        """Not yet implemented for pipeline use (P2 feature)."""
        raise NotImplementedError(
            "iFlytek lfasr is a P2 feature for long audio pretranscription. "
            "It is not available as a default short-clip ASR provider."
        )

    def _generate_signa(self, ts: str) -> str:
        """Generate iFlytek signature.

        signa = Base64(HmacSHA1(MD5(appid + ts), secretkey))
        """
        md5_hash = hashlib.md5((self._app_id + ts).encode("utf-8")).hexdigest()
        hmac_digest = hmac.new(
            self._secret_key.encode("utf-8"),
            md5_hash.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(hmac_digest).decode("utf-8")
