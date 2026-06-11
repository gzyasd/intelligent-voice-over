from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from ivo.core.user_settings import UserSettingsStore
    from ivo.ui.main_window import MainWindow
    from ivo.ui.theme import apply_app_theme
    from ivo.workspace_paths import default_user_settings_path

    app = QApplication(sys.argv)

    # Load user settings and apply theme
    root = Path.cwd().resolve()
    settings_store = UserSettingsStore(
        default_user_settings_path(root=root),
        runtime_root=root,
    )
    settings = settings_store.load()
    apply_app_theme(app, mode=settings.theme)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
