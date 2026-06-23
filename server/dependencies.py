"""依赖注入：提供共享的服务实例"""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from ivo.core.user_settings import UserSettingsStore
from ivo.model_services.adapter_factory import _infer_runtime_root
from ivo.model_services.provider_registry import ProviderRegistry
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.secret_store import SecretStore
from ivo.workspace_paths import default_config_dir, default_user_settings_path

# Runtime resource root: project root in development, bundled resources in packaged builds.
_RUNTIME_ROOT = _infer_runtime_root()
_USER_DATA_ROOT = Path(os.environ.get("IVO_USER_DATA_DIR", _RUNTIME_ROOT)).resolve()


def get_runtime_root() -> Path:
    return _RUNTIME_ROOT


def get_user_data_root() -> Path:
    return _USER_DATA_ROOT


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """从 pyproject.toml 读取版本号，避免多处硬编码漂移。"""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.startswith("version = "):
                return line.split('"')[1]
    return "0.0.0"


def get_user_settings_store() -> UserSettingsStore:
    return UserSettingsStore(
        default_user_settings_path(root=_USER_DATA_ROOT),
        runtime_root=_USER_DATA_ROOT,
    )


def get_config_dir() -> Path:
    return default_config_dir(root=_USER_DATA_ROOT)


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


@lru_cache(maxsize=1)
def get_provider_store() -> ProviderStore:
    return ProviderStore(get_config_dir())


@lru_cache(maxsize=1)
def get_secret_store() -> SecretStore:
    return SecretStore(get_config_dir())


def reset_singletons() -> None:
    """测试辅助函数：清除缓存的单例，使下一个请求重新创建。"""
    get_provider_registry.cache_clear()
    get_provider_store.cache_clear()
    get_secret_store.cache_clear()
