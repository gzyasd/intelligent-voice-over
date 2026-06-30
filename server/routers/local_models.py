"""Local model service API."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ivo.core.user_settings import PYPI_MIRRORS
from ivo.model_services.local_models import (
    ALL_LOCAL_MODEL_SERVICES,
    DependencyStatus,
    compute_shared_dep_counts,
    find_venv_python,
    get_local_service,
    is_newer_version,
)
from ivo.subprocess_utils import utf8_env

from .. import dependencies

router = APIRouter()

# 安装锁：防止并发 pip install 导致 venv 损坏
_install_lock = asyncio.Lock()
_download_lock = asyncio.Lock()

DownloadSource = Literal["huggingface", "hf_mirror"]
_HF_DOWNLOAD_ENDPOINTS: dict[DownloadSource, str] = {
    "huggingface": "https://huggingface.co",
    "hf_mirror": "https://hf-mirror.com",
}


class InstallRequest(BaseModel):
    package_name: str
    venv_name: str = ".venv"
    force_reinstall: bool = False


class UpgradeRequest(BaseModel):
    package_name: str
    venv_name: str = ".venv"


class DownloadLocalModelRequest(BaseModel):
    source: DownloadSource = "huggingface"


def _models_root() -> Path:
    return dependencies.get_user_settings_store().load().models_dir.resolve()


def _get_pip_mirror_url() -> str:
    settings = dependencies.get_user_settings_store().load()
    return PYPI_MIRRORS.get(settings.pip_mirror, ("", ""))[1]


def _get_custom_pythons() -> dict[str, Path]:
    """从 UserSettings 读取自定义 venv 路径，返回 venv_name -> python Path 映射。

    用于 find_venv_python 和 check_dependency_status 的 custom_pythons 参数。
    """
    settings = dependencies.get_user_settings_store().load()
    result: dict[str, Path] = {}
    if settings.custom_venv_python is not None:
        result[".venv"] = settings.custom_venv_python
    if settings.custom_pyannote_python is not None:
        result[".venv-pyannote"] = settings.custom_pyannote_python
    return result


def _repo_id_from_huggingface_url(repo_url: str) -> str:
    raw = repo_url.strip().rstrip("/")
    if not raw:
        raise ValueError("empty Hugging Face repository URL")
    parsed = urlparse(raw)
    path = parsed.path.strip("/") if parsed.scheme else raw
    for marker in ("/tree/", "/blob/", "/resolve/"):
        if marker in path:
            path = path.split(marker, 1)[0]
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"invalid Hugging Face repository URL: {repo_url}")
    return "/".join(parts[:2])


def _snapshot_download_model(repo_id: str, target_dir: Path, endpoint: str) -> str:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - exercised through API error handling
        raise RuntimeError(
            "huggingface_hub is not installed. Please run `uv sync --dev` or reinstall IVO."
        ) from exc

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_download(
        repo_id=repo_id,
        local_dir=str(target_dir),
        endpoint=endpoint,
    )
    return str(snapshot_path)


async def _ensure_pip_available(venv_python: Path) -> tuple[bool, str]:
    """确保 venv 中有 pip，没有则通过 ensurepip 引导。

    uv sync 创建的 venv 默认不含 pip，需在使用前引导。
    返回 (ok, message)，ok=True 时 message 为空。
    """
    # 检查 pip 是否可用
    check = await asyncio.create_subprocess_exec(
        str(venv_python), "-m", "pip", "--version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=utf8_env(),
    )
    stdout_bytes, stderr_bytes = await check.communicate()
    if check.returncode == 0:
        return True, ""
    # 尝试 ensurepip 引导
    boot = await asyncio.create_subprocess_exec(
        str(venv_python), "-m", "ensurepip", "--upgrade",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=utf8_env(),
    )
    boot_stdout, boot_stderr = await boot.communicate()
    if boot.returncode == 0:
        return True, ""
    err = boot_stderr.decode("utf-8", errors="replace").strip()
    return False, f"ensurepip 失败：{err or '未知错误'}"


async def _run_pip_install(
    venv_python: Path,
    package_name: str,
    *,
    upgrade: bool = False,
    force_reinstall: bool = False,
    mirror_url: str = "",
) -> tuple[bool, str]:
    """Run pip install in a subprocess, return (ok, output)."""
    cmd = [str(venv_python), "-m", "pip", "install"]
    if mirror_url:
        cmd.extend(["-i", mirror_url])
    if upgrade:
        cmd.append("--upgrade")
    if force_reinstall:
        cmd.append("--force-reinstall")
    cmd.append(package_name)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=utf8_env(),
        )
    except OSError as exc:
        return False, str(exc)

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=600)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return False, f"pip install timed out after 600s for {package_name}"

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if process.returncode == 0:
        return True, stdout
    return False, stderr or stdout


@router.post("/{provider_key}/download")
async def download_local_model(
    provider_key: str,
    request: DownloadLocalModelRequest,
) -> dict[str, Any]:
    """Download a Hugging Face local model into the configured models directory."""
    if _download_lock.locked():
        raise HTTPException(status_code=409, detail="Another model download is already running.")

    svc = get_local_service(provider_key)
    if svc is None:
        raise HTTPException(status_code=404, detail=f"Local model does not exist: {provider_key}")
    if not svc.huggingface_repo:
        raise HTTPException(
            status_code=400,
            detail=(
                "This local model does not have a Hugging Face repository configured for "
                "automatic download."
            ),
        )

    endpoint = _HF_DOWNLOAD_ENDPOINTS[request.source]
    try:
        repo_id = _repo_id_from_huggingface_url(svc.huggingface_repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    target_dir = svc.resolve_model_path(_models_root())
    if target_dir.is_dir():
        return {
            "ok": True,
            "skipped": True,
            "provider_key": provider_key,
            "repo_id": repo_id,
            "source": request.source,
            "endpoint": endpoint,
            "local_dir": str(target_dir),
            "output": "Model directory already exists.",
        }

    async with _download_lock:
        try:
            snapshot_path = await asyncio.to_thread(
                _snapshot_download_model,
                repo_id,
                target_dir,
                endpoint,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - depends on network/provider responses
            return {
                "ok": False,
                "skipped": False,
                "provider_key": provider_key,
                "repo_id": repo_id,
                "source": request.source,
                "endpoint": endpoint,
                "local_dir": str(target_dir),
                "output": str(exc),
            }

    _invalidate_stage_groups_cache()
    return {
        "ok": True,
        "skipped": False,
        "provider_key": provider_key,
        "repo_id": repo_id,
        "source": request.source,
        "endpoint": endpoint,
        "local_dir": str(target_dir),
        "output": f"Downloaded to {snapshot_path}",
    }


@router.get("")
def list_local_models() -> list[dict[str, Any]]:
    """List all built-in local model services."""
    models_root = _models_root()
    result: list[dict[str, Any]] = []
    for svc in ALL_LOCAL_MODEL_SERVICES:
        resolved_path = svc.resolve_model_path(models_root)
        result.append(
            {
                "provider_key": svc.provider_key,
                "display_name": svc.display_name,
                "stage": svc.stage,
                "model_dir_name": svc.model_dir_name,
                "model_path": str(resolved_path),
                "default_device": svc.default_device,
                "supported_devices": svc.supported_devices,
                "precision_options": svc.precision_options,
                "license_name": svc.license_name,
                "license_url": svc.license_url,
                "license_notes": svc.license_notes,
                "commercial_ok": svc.commercial_ok,
                "huggingface_repo": svc.huggingface_repo,
                "source_url": svc.source_url,
                "model_dir_exists": resolved_path.is_dir(),
            }
        )
    return result


@router.get("/{provider_key}/readiness")
def check_readiness(provider_key: str) -> dict[str, Any]:
    """Check local model readiness."""
    svc = get_local_service(provider_key)
    if svc is None:
        raise HTTPException(status_code=404, detail=f"本地模型不存在: {provider_key}")
    result = svc.readiness_check(_models_root())
    return {
        "provider_key": result.provider_key,
        "stage": result.stage,
        "status": result.status,
        "model_dir_exists": result.model_dir_exists,
        "missing_dependencies": result.missing_dependencies,
        "messages": result.messages,
    }


@router.get("/{provider_key}/dependencies")
def check_dependencies(provider_key: str) -> list[dict[str, Any]]:
    """Check local model dependency status."""
    svc = get_local_service(provider_key)
    if svc is None:
        raise HTTPException(status_code=404, detail=f"本地模型不存在: {provider_key}")
    custom_pythons = _get_custom_pythons()
    deps = svc.check_dependency_status(custom_pythons=custom_pythons)
    return [
        {
            "package_name": dep.package_name,
            "import_name": dep.import_name,
            "status": dep.status,
            "version": dep.version,
            "latest_version": dep.latest_version,
            "venv_name": dep.venv_name,
            "pip_install_hint": dep.pip_install_hint,
        }
        for dep in deps
    ]


# ── 依赖管理 API ────────────────────────────────────────────────────────────


@router.get("/dependencies/all-status")
def get_all_dependencies_status() -> list[dict[str, Any]]:
    """获取所有本地模型服务的依赖状态，按阶段分组。"""
    custom_pythons = _get_custom_pythons()
    result: list[dict[str, Any]] = []
    for svc in ALL_LOCAL_MODEL_SERVICES:
        deps = svc.check_dependency_status(custom_pythons=custom_pythons)
        result.append(
            {
                "provider_key": svc.provider_key,
                "display_name": svc.display_name,
                "stage": svc.stage,
                "dependencies": [
                    {
                        "package_name": dep.package_name,
                        "import_name": dep.import_name,
                        "status": dep.status,
                        "version": dep.version,
                        "latest_version": dep.latest_version,
                        "venv_name": dep.venv_name,
                        "pip_install_hint": dep.pip_install_hint,
                        "can_upgrade": dep.can_upgrade,
                        "action_label": dep.action_label,
                    }
                    for dep in deps
                ],
            }
        )
    return result


_VENV_NOT_FOUND_MSG = (
    "未找到 venv '{venv}' 的 Python 解释器。"
    "请在设置页面配置自定义 venv 路径，"
    "或运行 scripts/copy-venv-to-install.ps1 将 .venv 复制到安装目录的 resources/ 下，"
    "或设置 IVO_LOCAL_PYTHON 环境变量指向有效的 Python 解释器路径。"
)


@router.post("/dependencies/install")
async def install_dependency(request: InstallRequest) -> dict[str, Any]:
    """安装单个依赖包（支持 force_reinstall 修复 broken 依赖）。"""
    if _install_lock.locked():
        raise HTTPException(status_code=409, detail="另一个安装任务正在进行中，请等待完成。")
    async with _install_lock:
        custom_pythons = _get_custom_pythons()
        venv_python = find_venv_python(
            request.venv_name,
            custom_python=custom_pythons.get(request.venv_name),
        )
        if venv_python is None:
            raise HTTPException(
                status_code=400,
                detail=_VENV_NOT_FOUND_MSG.format(venv=request.venv_name),
            )
        # 确保 pip 可用（uv sync 创建的 venv 默认无 pip）
        pip_ok, pip_msg = await _ensure_pip_available(venv_python)
        if not pip_ok:
            raise HTTPException(status_code=400, detail=f"pip 不可用：{pip_msg}")
        mirror_url = _get_pip_mirror_url()
        ok, output = await _run_pip_install(
            venv_python,
            request.package_name,
            force_reinstall=request.force_reinstall,
            mirror_url=mirror_url,
        )
        if ok:
            _invalidate_stage_groups_cache()
        return {"ok": ok, "output": output, "package_name": request.package_name}


@router.post("/dependencies/upgrade")
async def upgrade_dependency(request: UpgradeRequest) -> dict[str, Any]:
    """升级单个依赖包到最新版本。"""
    if _install_lock.locked():
        raise HTTPException(status_code=409, detail="另一个安装任务正在进行中，请等待完成。")
    async with _install_lock:
        custom_pythons = _get_custom_pythons()
        venv_python = find_venv_python(
            request.venv_name,
            custom_python=custom_pythons.get(request.venv_name),
        )
        if venv_python is None:
            raise HTTPException(
                status_code=400,
                detail=_VENV_NOT_FOUND_MSG.format(venv=request.venv_name),
            )
        # 确保 pip 可用
        pip_ok, pip_msg = await _ensure_pip_available(venv_python)
        if not pip_ok:
            raise HTTPException(status_code=400, detail=f"pip 不可用：{pip_msg}")
        mirror_url = _get_pip_mirror_url()
        ok, output = await _run_pip_install(
            venv_python,
            request.package_name,
            upgrade=True,
            mirror_url=mirror_url,
        )
        if ok:
            _invalidate_stage_groups_cache()
        return {"ok": ok, "output": output, "package_name": request.package_name}


@router.post("/dependencies/install-all-missing")
async def install_all_missing() -> dict[str, Any]:
    """一键安装所有缺失/broken 的依赖包（顺序执行）。"""
    if _install_lock.locked():
        raise HTTPException(status_code=409, detail="另一个安装任务正在进行中，请等待完成。")
    async with _install_lock:
        custom_pythons = _get_custom_pythons()
        # 收集所有缺失/broken 的依赖
        missing: list[tuple[str, str, bool]] = []  # (package_name, venv_name, force_reinstall)
        seen: set[str] = set()
        for svc in ALL_LOCAL_MODEL_SERVICES:
            for dep in svc.check_dependency_status(custom_pythons=custom_pythons):
                if dep.status in ("missing", "broken") and dep.package_name not in seen:
                    seen.add(dep.package_name)
                    missing.append((dep.package_name, dep.venv_name, dep.status == "broken"))

        mirror_url = _get_pip_mirror_url()
        results: list[dict[str, Any]] = []
        # 每个 venv 只需引导一次 pip
        pip_ensured: set[str] = set()
        for package_name, venv_name, force_reinstall in missing:
            venv_python = find_venv_python(
                venv_name,
                custom_python=custom_pythons.get(venv_name),
            )
            if venv_python is None:
                results.append({
                    "package_name": package_name,
                    "ok": False,
                    "output": _VENV_NOT_FOUND_MSG.format(venv=venv_name),
                })
                continue
            # 确保 pip 可用（同一 venv 只引导一次）
            if venv_name not in pip_ensured:
                pip_ok, pip_msg = await _ensure_pip_available(venv_python)
                pip_ensured.add(venv_name)
                if not pip_ok:
                    results.append({
                        "package_name": package_name,
                        "ok": False,
                        "output": f"pip 不可用：{pip_msg}",
                    })
                    continue
            ok, output = await _run_pip_install(
                venv_python,
                package_name,
                force_reinstall=force_reinstall,
                mirror_url=mirror_url,
            )
            results.append({
                "package_name": package_name,
                "ok": ok,
                "output": output,
            })

        succeeded = sum(1 for r in results if r["ok"])
        if succeeded:
            _invalidate_stage_groups_cache()
        return {
            "results": results,
            "total": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
        }


async def _fetch_latest_version(
    client: httpx.AsyncClient,
    package_name: str,
    *,
    mirror_url: str,
) -> str:
    urls = [f"https://pypi.org/pypi/{package_name}/json"]
    if mirror_url:
        json_base = mirror_url.rstrip("/").removesuffix("/simple").rstrip("/")
        if json_base:
            urls.append(f"{json_base}/pypi/{package_name}/json")
    for url in urls:
        try:
            response = await client.get(url)
            response.raise_for_status()
            version = response.json().get("info", {}).get("version", "")
            if version:
                return str(version)
        except (httpx.HTTPError, ValueError, AttributeError):
            continue
    return ""


@router.get("/dependencies/upgrade-check")
async def check_upgrade_available() -> dict[str, Any]:
    """并发检查所有已安装依赖的最新版本，不阻塞服务端事件循环。"""
    mirror_url = _get_pip_mirror_url()
    custom_pythons = _get_custom_pythons()
    installed: dict[str, str] = {}
    seen: set[str] = set()
    dependency_results = await asyncio.gather(
        *(
            asyncio.to_thread(
                svc.check_dependency_status,
                custom_pythons=custom_pythons,
            )
            for svc in ALL_LOCAL_MODEL_SERVICES
        )
    )
    for deps_status in dependency_results:
        for dep in deps_status:
            if dep.package_name in seen or dep.status != "installed":
                continue
            seen.add(dep.package_name)
            installed[dep.package_name] = dep.version

    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "ivo"}) as client:
        latest_versions = await asyncio.gather(
            *(
                _fetch_latest_version(client, package_name, mirror_url=mirror_url)
                for package_name in installed
            )
        )

    items: list[dict[str, Any]] = []
    for (package_name, current), latest in zip(installed.items(), latest_versions, strict=True):
        items.append({
            "package_name": package_name,
            "current_version": current,
            "latest_version": latest,
            "can_upgrade": is_newer_version(latest, current),
        })
    return {
        "items": items,
        "checked": sum(1 for item in items if item["latest_version"]),
        "failed": sum(1 for item in items if not item["latest_version"]),
    }


# ── 阶段分组端点 ────────────────────────────────────────────────────────────

# 阶段显示名映射
_STAGE_DISPLAY_NAMES: dict[str, str] = {
    "separation": "人声分离",
    "asr": "语音识别",
    "diarization": "说话人分离",
    "translation": "翻译",
    "tts": "语音合成",
}

# 阶段顺序
_STAGE_ORDER: list[str] = ["separation", "asr", "diarization", "translation", "tts"]


def _compute_model_readiness(
    svc: Any,
    models_root: Path,
    deps_status: list[Any],
) -> dict[str, Any]:
    """Compute combined readiness status from model dir + dependencies."""
    model_dir_exists = svc.check_model_dir(models_root)
    missing_deps = [d for d in deps_status if d.status == "missing"]
    broken_deps = [d for d in deps_status if d.status == "broken"]

    if missing_deps:
        status = "missing_deps"
    elif broken_deps:
        status = "broken_deps"
    elif not model_dir_exists:
        status = "missing_model"
    else:
        status = "ready"

    messages: list[str] = []
    if not model_dir_exists:
        if svc.huggingface_repo:
            messages.append(f"模型目录未下载，请从 {svc.huggingface_repo} 下载")
        else:
            messages.append(f"模型目录 '{svc.model_dir_name}' 不存在")
    for d in missing_deps:
        messages.append(f"缺少依赖：{d.package_name}")
    for d in broken_deps:
        messages.append(f"依赖损坏：{d.package_name}")

    return {
        "status": status,
        "model_dir_exists": model_dir_exists,
        "missing_dependencies": [d.package_name for d in missing_deps],
        "broken_dependencies": [d.package_name for d in broken_deps],
        "messages": messages,
    }


def _serialize_model_card(
    svc: Any,
    *,
    models_root: Path,
    deps_status: list[Any],
    shared_counts: dict[str, int],
) -> dict[str, Any]:
    resolved_path = svc.resolve_model_path(models_root)
    return {
        "provider_key": svc.provider_key,
        "display_name": svc.display_name,
        "stage": svc.stage,
        "model_dir_name": svc.model_dir_name,
        "model_path": str(resolved_path),
        "model_dir_exists": resolved_path.is_dir(),
        "default_device": svc.default_device,
        "supported_devices": svc.supported_devices,
        "precision_options": svc.precision_options,
        "license_name": svc.license_name,
        "license_url": svc.license_url,
        "license_notes": svc.license_notes,
        "commercial_ok": svc.commercial_ok,
        "huggingface_repo": svc.huggingface_repo,
        "source_url": svc.source_url,
        "recommended": svc.recommended,
        "tags": svc.tags,
        "readiness": _compute_model_readiness(svc, models_root, deps_status),
        "dependencies": [
            {
                "package_name": dep.package_name,
                "import_name": dep.import_name,
                "status": dep.status,
                "version": dep.version,
                "latest_version": dep.latest_version,
                "venv_name": dep.venv_name,
                "pip_install_hint": dep.pip_install_hint,
                "can_upgrade": dep.can_upgrade,
                "action_label": dep.action_label,
                "shared_by_count": shared_counts.get(dep.package_name, 1),
            }
            for dep in deps_status
        ],
    }


# stage-groups 缓存：避免短时间内重复检查（10 秒 TTL）
_STAGE_GROUPS_CACHE_TTL = 10.0
_stage_groups_cache_data: dict[str, Any] | None = None
_stage_groups_cache_ts = 0.0


def _invalidate_stage_groups_cache() -> None:
    global _stage_groups_cache_data, _stage_groups_cache_ts
    _stage_groups_cache_data = None
    _stage_groups_cache_ts = 0.0


@router.get("/{provider_key}/status")
async def get_local_model_status(provider_key: str) -> dict[str, Any]:
    """只检测一个模型卡片，避免触发全列表加载状态。"""
    svc = get_local_service(provider_key)
    if svc is None:
        raise HTTPException(status_code=404, detail=f"本地模型不存在: {provider_key}")
    deps_status = await asyncio.to_thread(
        svc.check_dependency_status,
        custom_pythons=_get_custom_pythons(),
    )
    return _serialize_model_card(
        svc,
        models_root=_models_root(),
        deps_status=deps_status,
        shared_counts=compute_shared_dep_counts(),
    )


@router.get("/stage-groups")
async def get_stage_groups() -> dict[str, Any]:
    """获取按阶段分组的本地模型完整状态（模型文件 + 依赖 + 就绪状态）。

    并行检查所有模型的依赖状态，并使用 10 秒内存缓存避免重复检查。

    返回结构：
    {
      "stages": [
        {
          "stage": "separation",
          "display_name": "人声分离",
          "ready_count": 1,
          "total_count": 1,
          "models": [LocalModelCard, ...]
        }
      ],
      "summary": {
        "total_models": 8,
        "ready_models": 3,
        "missing_models": 5,
        "missing_deps_count": 7
      }
    }
    """
    # 检查缓存
    import time as _time

    global _stage_groups_cache_data, _stage_groups_cache_ts
    now = _time.time()
    if (
        _stage_groups_cache_data is not None
        and now - _stage_groups_cache_ts < _STAGE_GROUPS_CACHE_TTL
    ):
        return _stage_groups_cache_data

    models_root = _models_root()
    shared_counts = compute_shared_dep_counts()
    custom_pythons = _get_custom_pythons()

    # 并行检查所有模型的依赖状态（在线程池中运行同步的 check_dependency_status）
    import asyncio

    # 注意：LocalModelService 是 dataclass，不可哈希，不能作为 dict 的键。
    # 用 provider_key（字符串）作为键，避免 TypeError: unhashable type。
    deps_tasks: dict[str, asyncio.Future[list[DependencyStatus]]] = {
        svc.provider_key: asyncio.ensure_future(
            asyncio.to_thread(svc.check_dependency_status, custom_pythons=custom_pythons)
        )
        for svc in ALL_LOCAL_MODEL_SERVICES
    }
    deps_results: dict[str, list[DependencyStatus]] = {}
    for key, task in deps_tasks.items():
        deps_results[key] = await task

    # 按阶段分组
    stages_map: dict[str, list[Any]] = {}
    for svc in ALL_LOCAL_MODEL_SERVICES:
        stages_map.setdefault(svc.stage, []).append(svc)

    stages_result: list[dict[str, Any]] = []
    total_models = 0
    ready_models = 0
    missing_models = 0
    missing_deps_count = 0

    for stage in _STAGE_ORDER:
        services = stages_map.get(stage, [])
        if not services:
            continue

        models_cards: list[dict[str, Any]] = []
        stage_ready = 0
        for svc in services:
            total_models += 1
            deps_status = deps_results[svc.provider_key]
            card = _serialize_model_card(
                svc,
                models_root=models_root,
                deps_status=deps_status,
                shared_counts=shared_counts,
            )
            readiness = card["readiness"]

            if readiness["status"] == "ready":
                ready_models += 1
                stage_ready += 1
            else:
                missing_models += 1

            # 统计缺失/损坏依赖数（去重）
            for d in deps_status:
                if d.status in ("missing", "broken"):
                    missing_deps_count += 1

            models_cards.append(card)

        stages_result.append({
            "stage": stage,
            "display_name": _STAGE_DISPLAY_NAMES.get(stage, stage),
            "ready_count": stage_ready,
            "total_count": len(services),
            "models": models_cards,
        })

    result = {
        "stages": stages_result,
        "summary": {
            "total_models": total_models,
            "ready_models": ready_models,
            "missing_models": missing_models,
            "missing_deps_count": missing_deps_count,
        },
    }

    # 更新缓存
    _stage_groups_cache_data = result
    _stage_groups_cache_ts = now
    return result
