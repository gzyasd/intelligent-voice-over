from __future__ import annotations

from pathlib import Path


def test_default_local_command_profile_prefers_gpu_when_nvidia_is_available(
    tmp_path: Path,
) -> None:
    from ivo.profile_defaults import default_local_command_profiles_path

    examples = tmp_path / "examples"
    examples.mkdir()
    gpu = examples / "local_command_profiles.real_separation_asr_tts_f5_gpu_small.json"
    cpu = examples / "local_command_profiles.real_separation_asr_tts_f5_cpu_small.json"
    gpu.write_text("{}", encoding="utf-8")
    cpu.write_text("{}", encoding="utf-8")

    assert (
        default_local_command_profiles_path(
            root=tmp_path,
            nvidia_tool_available=True,
        )
        == gpu
    )


def test_default_local_command_profile_falls_back_to_cpu_without_nvidia(
    tmp_path: Path,
) -> None:
    from ivo.profile_defaults import default_local_command_profiles_path

    examples = tmp_path / "examples"
    examples.mkdir()
    gpu = examples / "local_command_profiles.real_separation_asr_tts_f5_gpu_small.json"
    cpu = examples / "local_command_profiles.real_separation_asr_tts_f5_cpu_small.json"
    gpu.write_text("{}", encoding="utf-8")
    cpu.write_text("{}", encoding="utf-8")

    assert (
        default_local_command_profiles_path(
            root=tmp_path,
            nvidia_tool_available=False,
        )
        == cpu
    )


def test_default_local_command_profile_uses_cpu_when_gpu_file_is_missing(
    tmp_path: Path,
) -> None:
    from ivo.profile_defaults import default_local_command_profiles_path

    examples = tmp_path / "examples"
    examples.mkdir()
    cpu = examples / "local_command_profiles.real_separation_asr_tts_f5_cpu_small.json"
    cpu.write_text("{}", encoding="utf-8")

    assert (
        default_local_command_profiles_path(
            root=tmp_path,
            nvidia_tool_available=True,
        )
        == cpu
    )
