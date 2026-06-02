from __future__ import annotations


def build_ai_dubbing_metadata(*, source_language: str, target_language: str) -> dict[str, str]:
    return {
        "ai_dubbing": "true",
        "ai_dubbing_notice": "AI generated dubbing",
        "source_language": source_language,
        "target_language": target_language,
    }
