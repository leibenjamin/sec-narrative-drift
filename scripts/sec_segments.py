from __future__ import annotations

from typing import Any

ABBREVIATIONS = {
    "al",
    "approx",
    "art",
    "bros",
    "co",
    "corp",
    "dr",
    "etc",
    "fig",
    "inc",
    "jr",
    "ltd",
    "mr",
    "mrs",
    "ms",
    "no",
    "prof",
    "sr",
    "st",
    "u.k",
    "u.s",
    "vs",
}

TRAILING_CLOSE = "\"')]} "


def _normalize_token(token: str) -> str:
    return token.strip(" \t\r\n\"'()[]{}").rstrip(".").lower()


def _looks_like_decimal(text: str, index: int) -> bool:
    return (
        0 < index < len(text) - 1
        and text[index] == "."
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


def _previous_token(text: str, index: int) -> str:
    cursor = index - 1
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1
    end = cursor + 1
    while cursor >= 0 and (text[cursor].isalnum() or text[cursor] in "._-"):
        cursor -= 1
    return text[cursor + 1 : end]


def _is_abbreviation(text: str, index: int) -> bool:
    token = _normalize_token(_previous_token(text, index + 1))
    if not token:
        return False
    if token in ABBREVIATIONS:
        return True
    if len(token) == 1 and token.isalpha():
        return True
    if "." in token and len(token) <= 5:
        return True
    return False


def _advance_sentence_end(text: str, index: int) -> int:
    cursor = index + 1
    while cursor < len(text) and text[cursor] in TRAILING_CLOSE:
        cursor += 1
    return cursor


def _find_sentence_boundaries(text: str) -> list[tuple[int, int]]:
    boundaries: list[tuple[int, int]] = []
    start = 0
    index = 0

    while index < len(text):
        char = text[index]

        if char in ".?!":
            if _looks_like_decimal(text, index) or _is_abbreviation(text, index):
                index += 1
                continue

            end = _advance_sentence_end(text, index)
            if end > start:
                boundaries.append((start, end))
                start = end
            index = end
            continue

        if char == "\n":
            run_end = index
            while run_end < len(text) and text[run_end] == "\n":
                run_end += 1
            if run_end - index >= 2:
                if index > start:
                    boundaries.append((start, index))
                start = run_end
                index = run_end
                continue

        index += 1

    if start < len(text):
        boundaries.append((start, len(text)))

    return boundaries


def segment_text_v1(text: str) -> dict[str, Any]:
    sentences: list[dict[str, int]] = []

    for start, end in _find_sentence_boundaries(text):
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if end <= start:
            continue
        sentences.append(
            {
                "sentence_id": len(sentences),
                "start": start,
                "end": end,
            }
        )

    return {
        "version": 1,
        "char_count": len(text),
        "sentence_count": len(sentences),
        "sentences": sentences,
    }
