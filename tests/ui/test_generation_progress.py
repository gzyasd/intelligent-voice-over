from __future__ import annotations


def test_generation_progress_updates_stage_and_tts_item(qtbot, tmp_path) -> None:
    from ivo.pipeline.progress import PipelineProgressEvent
    from ivo.ui.generation_progress import GenerationProgressPanel

    panel = GenerationProgressPanel()
    qtbot.addWidget(panel)

    panel.handle_progress(
        PipelineProgressEvent(
            stage="tts",
            stage_label="生成配音",
            status="progress",
            message="正在生成第 2 / 5 句：seg-002",
            overall_percent=76,
            current_item=2,
            total_items=5,
            output_path=tmp_path / "seg-002.wav",
        )
    )

    assert panel.overall_progress.value() == 76
    assert panel.current_stage_label.text() == "生成配音"
    assert panel.current_item_label.text() == "第 2 / 5 句"
    assert "seg-002" in panel.detail_label.text()
    assert panel.stage_status("tts") == "progress"


def test_generation_progress_shows_failure_with_recovery_hint(qtbot) -> None:
    from ivo.pipeline.progress import PipelineProgressEvent
    from ivo.ui.generation_progress import GenerationProgressPanel

    panel = GenerationProgressPanel()
    qtbot.addWidget(panel)

    panel.handle_progress(
        PipelineProgressEvent(
            stage="translation",
            stage_label="翻译改写",
            status="failed",
            message="LM Studio 未连接",
            overall_percent=50,
        )
    )

    assert panel.stage_status("translation") == "failed"
    assert "LM Studio 未连接" in panel.failure_label.text()
    assert "模型中心" in panel.recovery_hint_label.text()


def test_generation_progress_shows_elapsed_time(qtbot) -> None:
    from ivo.ui.generation_progress import GenerationProgressPanel

    panel = GenerationProgressPanel()
    qtbot.addWidget(panel)

    panel.set_elapsed_seconds(125)

    assert panel.elapsed_label.text() == "已用时 02:05"


def test_generation_progress_pause_resume_buttons_emit_signals(qtbot) -> None:
    from ivo.ui.generation_progress import GenerationProgressPanel
    from ivo.ui.theme import WARNING

    panel = GenerationProgressPanel()
    qtbot.addWidget(panel)
    events: list[str] = []
    panel.pause_requested.connect(lambda: events.append("pause"))
    panel.resume_requested.connect(lambda: events.append("resume"))

    panel.set_running_controls()
    panel.pause_button.click()
    panel.set_paused_controls()
    panel.resume_button.click()

    assert events == ["pause", "resume"]
    assert panel.pause_button.text() == "暂停"
    assert panel.resume_button.text() == "继续"
    assert WARNING in panel.overall_progress.styleSheet()
