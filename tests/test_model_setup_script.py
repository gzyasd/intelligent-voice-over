from __future__ import annotations

from pathlib import Path


def test_model_setup_script_filters_stage_and_prepares_model_dirs(tmp_path: Path) -> None:
    from ivo.model_setup import build_model_setup_script

    models_dir = tmp_path / "models"

    script = build_model_setup_script(models_dir, stage="tts")

    assert "$ErrorActionPreference = \"Stop\"" in script
    assert "tts / CosyVoice" in script
    assert "tts / f5_tts" in script
    assert "faster-whisper" not in script
    assert f"New-Item -ItemType Directory -Force -Path '{models_dir / 'tts' / 'F5-TTS'}'" in script
    assert f"--local-dir '{models_dir / 'tts' / 'F5-TTS'}'" in script
    assert "HF_TOKEN" in script


def test_setup_script_mentions_license_and_gitignore(tmp_path: Path) -> None:
    from ivo.model_setup import write_setup_script

    output = tmp_path / "setup.ps1"

    write_setup_script(output, models_dir=tmp_path / "models", stage=None)

    text = output.read_text(encoding="utf-8")
    assert "确认模型许可证" in text
    assert "不要提交 models/" in text
    assert "huggingface-cli login" in text


def test_example_setup_script_documents_safe_model_downloads() -> None:
    text = Path("scripts/setup-local-models.example.ps1").read_text(encoding="utf-8")

    assert "确认模型许可证" in text
    assert "不要提交 models/" in text
    assert "uv sync --extra local-separation" in text
    assert "uv sync --extra local-tts-f5" in text
    assert "uv sync --extra local-tts-cosyvoice" in text
    assert "huggingface-cli login" in text
    assert "huggingface-cli download Systran/faster-whisper-large-v3" in text
    assert "huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512" in text
    assert "huggingface-cli download SWivid/F5-TTS" in text
    assert "huggingface-cli download Qwen/Qwen3-8B" in text


def test_model_setup_script_comments_manual_download_steps(tmp_path: Path) -> None:
    from ivo.model_setup import build_model_setup_script

    script = build_model_setup_script(tmp_path / "models", stage="separation")

    assert "separation / demucs" in script
    assert "# Download: Demucs downloads named checkpoints on first use." in script
    assert "uv sync --extra local-separation" in script


def test_model_setup_script_comments_llm_server_framework_installs(tmp_path: Path) -> None:
    from ivo.model_setup import build_model_setup_script

    script = build_model_setup_script(tmp_path / "models", stage="translation")

    assert "# Manual install: install vLLM in a supported serving environment" in script
    assert "# Manual install: install SGLang in a supported serving environment" in script
    assert "\nuv pip install vllm\n" not in script
    assert "\nuv pip install sglang\n" not in script
