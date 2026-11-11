"""
preprocessor.py
Cleans and segments meeting transcripts into structured speaker turns and sentences.
"""

import re
from typing import List, Dict, Any


def clean_text(text: str) -> str:
    """Normalizes whitespace, special quotes, and line breaks."""
    if not text:
        return ""
    # Normalize curly quotes and dashes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("—", " - ").replace("–", " - ")
    # Normalize newlines
    text = re.sub(r"\r\n|\r", "\n", text)
    # Strip unnecessary trailing spaces per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def parse_dialogue_turns(transcript_text: str) -> List[Dict[str, Any]]:
    """
    Segments a meeting transcript into individual dialogue turns.
    Handles common transcript formats:
      - [00:01] Carlos: Text...
      - Carlos (Lead): Text...
      - Alice: Text...
      - Line breaks with continuous speaker speech
    """
    cleaned = clean_text(transcript_text)
    if not cleaned:
        return []

    # Regex for Speaker format with optional timestamp:
    # e.g., "[00:15] Sarah:" or "Sarah Smith:" or "Sarah (PM):" or "10:15 AM - Bob:"
    speaker_pattern = re.compile(
        r"^(?:\[?[\d]{1,2}:[\d]{2}(?::[\d]{2})?(?:\s*[AP]M)?\]?\s*[-–]?\s*)?"  # Optional timestamp
        r"([A-Z][a-zA-Z0-9_\s\.\(\)\-]{1,35}?)"                                # Speaker Name
        r"\s*:\s*(.*)$",                                                       # Separator and utterance
        re.MULTILINE
    )

    turns: List[Dict[str, Any]] = []
    current_turn = None

    for line in cleaned.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = speaker_pattern.match(line)
        if match:
            # New speaker turn detected
            if current_turn:
                turns.append(current_turn)

            speaker = match.group(1).strip()
            # Clean off any role in parentheses from speaker name if desired, or keep as display
            speaker_clean = re.sub(r"\(.*?\)", "", speaker).strip() or speaker

            utterance = match.group(2).strip()
            current_turn = {
                "speaker": speaker_clean,
                "raw_speaker": speaker,
                "text": utterance,
                "sentences": split_into_sentences(utterance)
            }
        else:
            if current_turn:
                # Continuation of current speaker's turn
                current_turn["text"] += " " + line
                current_turn["sentences"] = split_into_sentences(current_turn["text"])
            else:
                # No speaker detected yet (e.g., initial paragraph or header)
                turns.append({
                    "speaker": "Unknown",
                    "raw_speaker": "Unknown",
                    "text": line,
                    "sentences": split_into_sentences(line)
                })

    if current_turn:
        turns.append(current_turn)

    return turns


def split_into_sentences(text: str) -> List[str]:
    """Splits an utterance into sentences while preserving abbreviations."""
    if not text:
        return []
    # Avoid splitting on common abbreviations like e.g., i.e., Dr., vs., etc.
    sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+')
    sentences = [s.strip() for s in sentence_end.split(text) if s.strip()]
    return sentences or [text.strip()]
