from __future__ import annotations


def test_classifies_successful_tqdm_stderr_as_progress() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="separation",
            provider="demucs",
            command=["python", "demucs.py"],
            stdout="Separated track",
            stderr="0%| | 0/10 [00:00<?, ?it/s]\n100%|████| 10/10 [00:01<00:00, 8.0it/s]",
            exit_code=0,
        )
    )

    assert [entry.level for entry in entries] == ["info", "progress"]
    assert entries[1].title == "命令进度"
    assert "命令错误输出" not in entries[1].text


def test_classifies_nonzero_stderr_as_error() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="tts",
            provider="f5",
            command=["python", "tts.py"],
            stderr="model missing",
            exit_code=1,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "error"
    assert entries[0].title == "命令执行失败"
    assert "退出码：1" in entries[0].text
    assert "model missing" in entries[0].text


def test_classifies_successful_warning_stderr_as_warning() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="tts",
            provider="f5",
            command=["python", "tts.py"],
            stderr="FutureWarning: Python 3.10 support will stop later",
            exit_code=0,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "warning"
    assert entries[0].title == "命令警告"


def test_summarizes_pyannote_torchcodec_warning() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    stderr = "\n".join(
        [
            "torchcodec is not installed correctly so built-in audio decoding will fail.",
            "Traceback (most recent call last):",
            "FileNotFoundError: Could not find module 'libtorchcodec_core8.dll'",
            "[end of libtorchcodec loading traceback].",
        ]
    )

    entries = classify_command_log(
        CommandExecutionLog(
            stage="diarization",
            provider="pyannote",
            command=["python", "pyannote_diarization.py"],
            stderr=stderr,
            exit_code=0,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "warning"
    assert entries[0].title == "环境提示"
    assert "当前流程已使用 soundfile 预加载音频" in entries[0].text


def test_summarizes_google_python_future_warning() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="tts",
            provider="f5",
            command=["python", "tts.py"],
            stderr=(
                "D:\\\\.venv\\\\lib\\\\site-packages\\\\google\\\\api_core\\\\_python_version_support.py:255: "
                "FutureWarning: You are using a Python version (3.10.6) which Google will stop supporting..."
            ),
            exit_code=0,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "warning"
    assert entries[0].title == "依赖提示"
    assert "Google API 依赖提示 Python 3.10 未来支持周期" in entries[0].text


def test_classifies_non_tqdm_non_warning_stderr_as_info() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="asr",
            provider="whisper",
            command=["python", "asr.py"],
            stderr="Using fallback decoder",
            exit_code=0,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "info"
    assert entries[0].title == "命令附加输出"


def test_classifies_stdout_only_as_info() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="separation",
            provider="demucs",
            command=["python", "demucs.py"],
            stdout="Done",
            exit_code=0,
        )
    )

    assert len(entries) == 1
    assert entries[0].level == "info"
    assert entries[0].title == "命令输出"


def test_classifies_empty_log_as_no_entries() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="tts",
            provider="f5",
            command=["python", "tts.py"],
            exit_code=0,
        )
    )

    assert entries == []


def test_classifies_nonzero_exit_without_stderr_as_error() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    entries = classify_command_log(
        CommandExecutionLog(
            stage="asr",
            provider="faster-whisper",
            command=["python", "asr.py"],
            stdout="loading model",
            stderr="",
            exit_code=2,
        )
    )

    assert [entry.level for entry in entries] == ["info", "error"]
    assert entries[1].title == "命令执行失败"
    assert "退出码：2" in entries[1].text
    assert "没有错误输出" in entries[1].text
    assert entries[1].full_text is not None
    assert "没有错误输出" in entries[1].full_text


def test_summarized_warning_keeps_full_stderr_for_copying() -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.log_classification import classify_command_log

    stderr = "\n".join(
        [
            "torchcodec is not installed correctly so built-in audio decoding will fail.",
            "Traceback (most recent call last):",
            "FileNotFoundError: Could not find module 'libtorchcodec_core8.dll'",
            "[end of libtorchcodec loading traceback].",
        ]
    )

    entries = classify_command_log(
        CommandExecutionLog(
            stage="diarization",
            provider="pyannote-community-1-local",
            command=["python", "pyannote_diarization.py"],
            stderr=stderr,
            exit_code=0,
        )
    )

    assert entries[0].title == "环境提示"
    assert "Traceback" not in entries[0].text
    assert entries[0].full_text is not None
    assert "Traceback (most recent call last):" in entries[0].full_text
    assert "libtorchcodec_core8.dll" in entries[0].full_text
