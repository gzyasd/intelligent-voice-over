"""Provider configuration data models for the model services system."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ivo.model_services.stages import STAGE_NAMES, StageName

ProviderKind = Literal["api", "local"]
ProviderProtocol = str


class ProviderCapability(BaseModel):
    """Describes what a provider can produce for a given stage."""

    stage: StageName
    output_keys: list[str]
    can_merge_with: list[StageName] = Field(default_factory=list)


class SecretRef(BaseModel):
    """Reference to an encrypted secret in the SecretStore."""

    id: str
    label: str

    @field_validator("id", "label")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class ProviderAccount(BaseModel):
    """Vendor account credentials (no plaintext secrets stored here)."""

    id: str
    display_name: str
    provider_key: str
    kind: ProviderKind
    enabled: bool = True
    api_base_url: str = ""
    api_key_ref: str | None = None
    auth_fields: dict[str, str] = Field(default_factory=dict)
    extra: dict[str, object] = Field(default_factory=dict)
    last_validation_status: str = "unchecked"
    last_validation_message: str = "尚未验证"

    @field_validator("id", "display_name", "provider_key")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class StageProviderConfig(BaseModel):
    """Per-stage configuration binding a provider account to pipeline parameters."""

    id: str
    display_name: str
    account_id: str | None = None
    provider_key: str
    kind: ProviderKind
    stage: StageName
    protocol: ProviderProtocol
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    model_name: str = ""
    local_model_path: str = ""
    device: str = "auto"
    precision: str = "auto"
    quality_preset: str = "balanced"
    upload_media_to_cloud: bool = False
    extra: dict[str, object] = Field(default_factory=dict)
    last_validation_status: str = "unchecked"
    last_validation_message: str = "尚未验证"

    @field_validator("id", "display_name", "provider_key")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("protocol")
    @classmethod
    def require_non_empty_protocol(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("protocol cannot be empty")
        return value

    @field_validator("stage")
    @classmethod
    def require_valid_stage(cls, value: str) -> str:
        if value not in STAGE_NAMES:
            valid = ", ".join(STAGE_NAMES)
            raise ValueError(f"invalid stage: {value!r}, must be one of: {valid}")
        return value


class SchemeStageBinding(BaseModel):
    """Binds a pipeline stage to a specific StageProviderConfig within a scheme."""

    stage: StageName
    stage_config_id: str
    execution_group: str | None = None
    skip_when_execution_group_has_output: bool = False

    @field_validator("stage_config_id")
    @classmethod
    def require_non_empty_config_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stage_config_id cannot be empty")
        return value


class DubbingScheme(BaseModel):
    """A named combination of stage provider configs for a complete dubbing pipeline."""

    id: str
    display_name: str
    description: str = ""
    bindings: list[SchemeStageBinding]
    prefer_gpu: bool = True
    content_types: list[str] = Field(default_factory=lambda: ["通用"])

    @field_validator("id", "display_name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    def get_binding_for_stage(self, stage: StageName) -> SchemeStageBinding | None:
        """Find the binding for a specific stage, if any."""
        for binding in self.bindings:
            if binding.stage == stage:
                return binding
        return None

    def list_bound_stages(self) -> list[StageName]:
        """Return stages that have bindings in this scheme."""
        return [binding.stage for binding in self.bindings]
