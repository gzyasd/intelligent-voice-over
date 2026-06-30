from __future__ import annotations

from pathlib import Path


def test_create_project_dialog_loads_and_submits_scheme_selection() -> None:
    source = Path("src/components/CreateProjectDialog.vue").read_text(encoding="utf-8")
    types = Path("src/types/index.ts").read_text(encoding="utf-8")

    assert "NModal" in source
    assert "useModelServicesStore" in source
    assert "schemeOptions" in source
    assert "selectedSchemeId" in source
    assert 'NFormItem label="配音方案"' in source
    assert "scheme_id: selectedSchemeId.value" in source
    assert "scheme_id?: string | null" in types


def test_create_project_is_opened_as_dialog_from_home_and_library() -> None:
    home = Path("src/pages/Home.vue").read_text(encoding="utf-8")
    library = Path("src/pages/ProjectLibrary.vue").read_text(encoding="utf-8")

    assert "CreateProjectDialog" in home
    assert "v-model:show=\"showCreateDialog\"" in home
    assert "router.push('/create')" not in home

    assert "CreateProjectDialog" in library
    assert "v-model:show=\"showCreateDialog\"" in library
    assert "router.push('/create')" not in library


def test_create_project_no_longer_has_sidebar_menu_or_route() -> None:
    layout = Path("src/components/layout/AppLayout.vue").read_text(encoding="utf-8")
    router = Path("src/router/index.ts").read_text(encoding="utf-8")

    assert "新建项目" not in layout
    assert "key: '/create'" not in layout
    assert "path: '/create'" not in router
    assert "CreateProject.vue" not in router


def test_app_layout_keeps_sidebar_fixed_while_content_scrolls() -> None:
    source = Path("src/components/layout/AppLayout.vue").read_text(encoding="utf-8")

    assert 'class="app-sider"' in source
    assert 'class="app-main"' in source
    assert ".app-layout" in source and "height: 100vh" in source
    assert ".app-sider" in source and "overflow: hidden" in source
    assert ".app-main" in source and "overflow: hidden" in source
    assert ".app-content" in source and "overflow-y: auto" in source
