from __future__ import annotations


def test_settings_page_saves_user_settings(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.settings_page import SettingsPage

    models_dir = tmp_path / "models-custom"
    projects_dir = tmp_path / "runs-custom"
    monkeypatch.setattr(
        "ivo.ui.settings_page.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(models_dir),
    )
    page = SettingsPage(settings_path=tmp_path / ".ivo-work" / "user-settings.json", runtime_root=tmp_path)
    qtbot.addWidget(page)

    page.browse_models_button.click()
    page.projects_dir_edit.setText(str(projects_dir))
    page.prefer_gpu_checkbox.setChecked(False)
    page.lm_studio_url_edit.setText("http://127.0.0.1:1995/v1")
    page.save_button.click()

    saved = page.store.load()
    assert saved.models_dir == models_dir
    assert saved.projects_dir == projects_dir
    assert saved.prefer_gpu is False
    assert page.status_label.text() == "设置已保存"


def test_main_window_settings_save_updates_model_center(qtbot, tmp_path) -> None:
    from ivo.core.user_settings import UserSettings
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    settings = UserSettings.with_defaults(runtime_root=tmp_path).model_copy(
        update={"models_dir": tmp_path / "models-custom"}
    )

    window.handle_user_settings_saved(settings)

    assert window.model_center.model_dir_edit.text() == str(tmp_path / "models-custom")
    assert window.model_settings.local_model_path_edit.text() == str(tmp_path / "models-custom")
