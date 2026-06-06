from __future__ import annotations


def test_app_shell_switches_between_named_pages(qtbot) -> None:
    from PySide6.QtWidgets import QLabel

    from ivo.ui.app_shell import AppShell

    shell = AppShell()
    qtbot.addWidget(shell)
    shell.add_page("home", "首页", QLabel("home"))
    shell.add_page("projects", "项目库", QLabel("projects"))

    assert shell.navigation_labels() == ["首页", "项目库"]
    assert shell.current_page_id() == "home"

    shell.set_current_page("projects")

    assert shell.current_page_id() == "projects"


def test_app_shell_clicking_navigation_button_changes_page(qtbot) -> None:
    from PySide6.QtWidgets import QLabel

    from ivo.ui.app_shell import AppShell

    shell = AppShell()
    qtbot.addWidget(shell)
    shell.add_page("home", "首页", QLabel("home"))
    shell.add_page("settings", "设置", QLabel("settings"))

    shell.navigation_button("设置").click()

    assert shell.current_page_id() == "settings"
