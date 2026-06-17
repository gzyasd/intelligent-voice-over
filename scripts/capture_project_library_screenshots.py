"""Capture project library page screenshots for visual review.

Outputs to scratch/ui-screenshots/project-library-review/ (not committed).
Run with: $env:QT_QPA_PLATFORM='offscreen'; uv run python scripts/capture_project_library_screenshots.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from ivo.core.project_library import ProjectLibraryItem
from ivo.ui.project_library_page import ProjectLibraryPage
from ivo.ui.theme import apply_app_theme


def _items(tmp_root: Path) -> list[ProjectLibraryItem]:
    return [
        ProjectLibraryItem(
            name=f"长标题项目 {i} - 日剧第{i}集智能配音",
            path=tmp_root / f"Project{i}.ivoproj",
            content_type="audio" if i % 2 else "video",
            source_language="ja" if i % 2 else "en",
            target_language="zh",
            updated_at=float(i),
            status="已完成" if i % 4 == 0 else ("生成中" if i % 4 == 1 else ("失败" if i % 4 == 2 else "未开始")),
            status_detail="总耗时 01:23:45" if i % 3 == 0 else ("正在生成配音 42%" if i % 4 == 1 else ""),
            final_output_path=(
                tmp_root / f"Project{i}.ivoproj" / "renders" / f"final_output_{i}.mp4"
            ) if i % 4 == 0 else None,
        )
        for i in range(10)
    ]


def _capture(page: ProjectLibraryPage, out_path: Path) -> None:
    page.show()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    # Wait for deferred reflow (QTimer.singleShot) to complete
    QTest.qWait(100)
    page.grab().save(str(out_path))
    page.close()


def main() -> int:
    out_dir = Path("scratch/ui-screenshots/project-library-review")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_root = Path("F:/runs")

    app = QApplication.instance() or QApplication(sys.argv)

    for theme in ("light", "dark"):
        apply_app_theme(app, theme)

        page = ProjectLibraryPage()
        page.resize(1280, 800)
        page.set_projects(_items(tmp_root))
        _capture(page, out_dir / f"{theme}-many-1280.png")

        page = ProjectLibraryPage()
        page.resize(760, 720)
        page.set_projects(_items(tmp_root))
        _capture(page, out_dir / f"{theme}-many-760.png")

        page = ProjectLibraryPage()
        page.resize(900, 650)
        page.set_projects([])
        _capture(page, out_dir / f"{theme}-empty.png")

        page = ProjectLibraryPage()
        page.resize(900, 650)
        page.set_projects(_items(tmp_root))
        page._search_edit.setText("不存在的项目")
        _capture(page, out_dir / f"{theme}-no-match.png")

    print(out_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
