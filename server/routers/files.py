"""文件代理 API（预览/下载）

安全限制：只允许访问已注册项目目录内的文件，防止路径遍历攻击。
项目目录通过 UserSettingsStore.projects_dir 和 recent_projects 推断。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .. import dependencies

router = APIRouter()


def _resolve_allowed_roots() -> list[Path]:
    """获取允许访问的根目录列表（项目库目录 + 最近项目）"""
    roots: list[Path] = []
    try:
        store = dependencies.get_user_settings_store()
        settings = store.load()
        roots.append(settings.projects_dir.resolve())
        for p in settings.recent_projects:
            try:
                roots.append(Path(p).resolve())
            except (OSError, ValueError):
                continue
    except Exception:
        # 设置加载失败时退化为空列表（拒绝所有访问）
        pass
    return roots


def _is_path_allowed(file_path: Path, allowed_roots: list[Path]) -> bool:
    """检查文件路径是否在允许的根目录内"""
    try:
        resolved = file_path.resolve()
    except (OSError, ValueError):
        return False
    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _validate_file_path(path: str) -> Path:
    """校验文件路径并返回 Path 对象"""
    if not path:
        raise HTTPException(status_code=400, detail="文件路径不能为空")

    file_path = Path(path)

    # 拒绝包含 .. 的原始路径（即使 resolve 后合法，也视为可疑）
    if ".." in file_path.parts:
        raise HTTPException(status_code=400, detail="路径不允许包含上级目录引用")

    # 校验路径在允许的根目录内
    allowed_roots = _resolve_allowed_roots()
    if not _is_path_allowed(file_path, allowed_roots):
        raise HTTPException(status_code=403, detail="无权访问该路径")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return file_path


@router.get("/preview")
def preview_file(path: str = Query(..., description="文件路径")) -> FileResponse:
    """预览音频/视频文件（支持 Range 请求）"""
    file_path = _validate_file_path(path)
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@router.get("/download")
def download_file(path: str = Query(..., description="文件路径")) -> FileResponse:
    """下载文件"""
    file_path = _validate_file_path(path)
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
        headers={"Content-Disposition": f"attachment; filename=\"{file_path.name}\""},
    )
