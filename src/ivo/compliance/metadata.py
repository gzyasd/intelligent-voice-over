from __future__ import annotations


def build_ai_dubbing_metadata(*, source_language: str, target_language: str) -> dict[str, str]:
    """Build AI dubbing metadata tags for FFmpeg output.

    Uses standard MP4/MOV container tags (title, artist, comment, genre)
    because FFmpeg does not persist custom keys (e.g. ai_dubbing) in MP4.
    The 'comment' field carries the structured AI dubbing notice so downstream
    tools can still parse it, while 'genre' marks the content as AI dubbed.
    """
    return {
        "title": f"AI Dubbed ({source_language} -> {target_language})",
        "artist": "Intelligent Voice Over",
        "comment": f"AI generated dubbing; source_language={source_language}; target_language={target_language}",
        "genre": "AI Dubbed",
    }
