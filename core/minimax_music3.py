"""MiniMax Music 3's text interchange contract (no model dependencies)."""

import json
import re

_HEADINGS = ("Global Metadata", "Vocal Details", "Arrangement")
_HEADING = re.compile(r"^(Global Metadata|Vocal Details|Arrangement):", re.MULTILINE)


def unfence_song_json(text: str) -> str:
    """Accept only a single enclosing JSON/plain code fence."""
    candidate = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", candidate, re.DOTALL | re.IGNORECASE)
    return match[1].strip() if match else candidate


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("MiniMax Music 3 JSON must not contain duplicate fields.")
        result[key] = value
    return result


def parse_song_json(text: str) -> dict[str, str]:
    """Validate without including user content in error messages."""
    if not isinstance(text, str):
        raise ValueError("MiniMax Music 3 requires a JSON string.")  # noqa: TRY004 - one validation error API
    try:
        song = json.loads(unfence_song_json(text), object_pairs_hook=_unique_fields)
    except json.JSONDecodeError:
        raise ValueError("MiniMax Music 3 requires valid JSON with caption and lyrics strings.") from None
    if not isinstance(song, dict) or set(song) != {"caption", "lyrics"}:
        raise ValueError("MiniMax Music 3 requires exactly caption and lyrics fields.")
    if not all(isinstance(value, str) for value in song.values()):
        raise ValueError("MiniMax Music 3 caption and lyrics must both be strings.")
    caption = song["caption"]
    if not caption.strip():
        raise ValueError("MiniMax Music 3 caption must not be empty.")
    matches = list(_HEADING.finditer(caption))
    if tuple(match[1] for match in matches) != _HEADINGS or matches[0].start() != 0:
        raise ValueError(
            "MiniMax Music 3 caption requires ordered headings: "
            "Global Metadata:, Vocal Details:, Arrangement:.",
        )
    return song

