from __future__ import annotations

from pathlib import Path


def test_create_project_page_loads_and_submits_scheme_selection() -> None:
    source = Path("src/pages/CreateProject.vue").read_text(encoding="utf-8")
    types = Path("src/types/index.ts").read_text(encoding="utf-8")

    assert "useModelServicesStore" in source
    assert "schemeOptions" in source
    assert "selectedSchemeId" in source
    assert 'NFormItem label="配音方案"' in source
    assert "scheme_id: selectedSchemeId.value" in source
    assert "scheme_id?: string | null" in types


def test_app_layout_keeps_sidebar_fixed_while_content_scrolls() -> None:
    source = Path("src/components/layout/AppLayout.vue").read_text(encoding="utf-8")

    assert 'class="app-sider"' in source
    assert 'class="app-main"' in source
    assert ".app-layout" in source and "height: 100vh" in source
    assert ".app-sider" in source and "overflow: hidden" in source
    assert ".app-main" in source and "overflow: hidden" in source
    assert ".app-content" in source and "overflow-y: auto" in source
