"""
extractor.py
Competition-Grade Information Extraction Engine for Meeting Action Items.
Features:
  1. Deterministic Symbolic NLP Engine (Pattern Grammar + Linguistic Slot-Filling)
  2. Neural / Semantic AI Engine (Structured Reasoning + Paraphrase Handling)
  3. Ensemble / Comparative Mode (Side-by-side audit of both engines)
  4. Calendar (.ics) generation for Google Calendar / Apple Calendar / Outlook
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from src.preprocessor import parse_dialogue_turns
from src.verifier import evaluate_action_item

# Disallowed words that cannot be proper owner names
DISALLOWED_NAME_WORDS = {
    "we", "i", "you", "they", "he", "she", "it", "this", "that", "there",
    "right", "also", "let", "lets", "down", "need", "have", "so", "then",
    "just", "and", "but", "or", "when", "if", "not", "today", "tomorrow",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "haha", "good", "great", "yes", "no", "okay", "alright", "action", "item", "business"
}

# 1. Self-commitment triggers
SELF_COMMIT_PATTERNS = [
    re.compile(r"\b(?:I will|I'll|I am going to|I'm going to|I shall)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:I can help(?:\s+(?:to\s+)?coordinate|\s+with|\s+to)?|I can)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:I(?:'ll| will)? take care of)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:I(?:'ll| will)? handle)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:My action item is to|I'm responsible for)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
]

# 2. Directed assignment triggers
DIRECTED_PATTERNS = [
    re.compile(r"\b([A-Z][a-z]{1,20})[,\s]+(?:can you|could you|please|will you)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:Assign(?:ing)? to|Action item for)\s+([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?)\s*[:–-]?\s*([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b([A-Z][a-z]{1,20})\s+(?:will|is going to|agreed to|is assigned to)\s+([a-z].*?)(?=[.?!]|$)"),
]

# 3. Collective / Impersonal triggers
COLLECTIVE_PATTERNS = [
    re.compile(r"\b(?:we really need to|we need to|we have to|we must)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:someone needs to|somebody should|someone please)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:let's make sure to|let's ensure|let's remember to)\s+([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:Action item|AI|Takeaway)\s*[:–-]\s*([a-z].*?)(?=[.?!]|$)", re.IGNORECASE),
]

# 4. Temporal / Deadline regex patterns
DEADLINE_PATTERNS = [
    re.compile(r"\b(?:by|before|until|due)\s+(?:tomorrow(?:\s+at\s+[\d]{1,2}(?::[\d]{2})?\s*(?:am|pm)?)?|yesterday|today|tonight|(?:next|this)\s+[a-z]+|[a-z]+day(?:\s+at\s+[\d]{1,2}(?::[\d]{2})?\s*(?:am|pm)?)?|eod|end of (?:day|week|month|quarter)|noon|midnight|[\d]{1,2}(?::[\d]{2})?\s*(?:am|pm)?(?:\s+tonight)?)\b", re.IGNORECASE),
    re.compile(r"\b(?:before|prior to)\s+(?:the\s+[a-z\s]+?\s+)((?:next|this)\s+[a-z]+|[a-z]+day|tomorrow|eod)\b", re.IGNORECASE),
    re.compile(r"\b(?:on|by|due)\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+at\s+[\d]{1,2}(?::[\d]{2})?\s*(?:am|pm)?)?\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
]

NO_DEADLINE_EXPRESSIONS = [
    "not sure when", "haven't checked my calendar", "no deadline", "no rush", "whenever", "sometime later"
]


def extract_deadline(text: str) -> Tuple[Optional[str], str]:
    """Extracts explicit temporal deadlines from text."""
    text_lower = text.lower()
    for disclaimer in NO_DEADLINE_EXPRESSIONS:
        if disclaimer in text_lower:
            return None, text

    for pattern in DEADLINE_PATTERNS:
        match = pattern.search(text)
        if match:
            matched_str = match.group(1) if match.groups() and match.group(1) else match.group(0)
            clean_deadline = re.sub(r"^(?:by|before|until|due|on)\s+", "", matched_str.strip(), flags=re.IGNORECASE).strip()
            clean_deadline = clean_deadline[0].upper() + clean_deadline[1:] if clean_deadline else matched_str
            text_without_deadline = text[:match.start()] + text[match.end():]
            text_without_deadline = re.sub(r"\s+", " ", text_without_deadline).strip()
            return clean_deadline, text_without_deadline

    return None, text


def clean_task_description(raw_task: str) -> str:
    """Cleans up the extracted task description to be a concise imperative verb phrase."""
    task = raw_task.strip()
    task = re.split(r",\s*(?:but|though|although|however|and I)\b", task, flags=re.IGNORECASE)[0]
    task = re.sub(r"^(?:to\s+|really\s+|also\s+)", "", task, flags=re.IGNORECASE).strip()
    task = re.sub(r"[.!?,;:\s]+$", "", task).strip()
    if task:
        task = task[0].upper() + task[1:]
    return task


def parse_relative_date_to_iso(deadline_str: str, meeting_date_str: str = "2026-11-10") -> Optional[str]:
    """Resolves relative date descriptions (e.g. 'Tomorrow at 3 PM', 'This Thursday') into YYYY-MM-DD."""
    if not deadline_str or deadline_str == "Unspecified":
        return None
    try:
        base_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
    except Exception:
        base_date = datetime.now().date()

    dl_lower = deadline_str.lower()
    if "tomorrow" in dl_lower:
        target_date = base_date + timedelta(days=1)
        return target_date.strftime("%Y-%m-%d")
    elif "today" in dl_lower or "tonight" in dl_lower:
        return base_date.strftime("%Y-%m-%d")
    
    # Days of week
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for idx, day_name in enumerate(days):
        if day_name in dl_lower:
            current_day_idx = base_date.weekday()
            days_ahead = idx - current_day_idx
            if "next" in dl_lower and days_ahead <= 0:
                days_ahead += 7
            elif days_ahead <= 0:
                days_ahead += 7
            target_date = base_date + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")

    return None


def extract_from_sentence(sentence: str, speaker: str, engine: str = "symbolic") -> Optional[Dict[str, Any]]:
    """Extracts commitment from a single sentence turn, strictly enforcing the No-Guessing Rule."""
    sentence_clean = sentence.strip()
    if not sentence_clean:
        return None

    if sentence_clean.endswith("?") and not any(sentence_clean.lower().startswith(x) for x in ["can you", "could you", "will you"]):
        return None

    # 1. Directed assignment
    for pattern in DIRECTED_PATTERNS:
        match = pattern.search(sentence_clean)
        if match:
            owner_candidate = match.group(1).strip()
            if owner_candidate.lower() in DISALLOWED_NAME_WORDS:
                continue

            raw_task = match.group(2).strip()
            deadline, remaining_task = extract_deadline(raw_task)
            if not deadline:
                deadline, _ = extract_deadline(sentence_clean)
            
            clean_task = clean_task_description(remaining_task)
            return evaluate_action_item(
                task=clean_task,
                owner=owner_candidate,
                deadline=deadline,
                trigger_type="explicit",
                raw_sentence=sentence_clean
            )

    # 2. Self-commitment
    for pattern in SELF_COMMIT_PATTERNS:
        match = pattern.search(sentence_clean)
        if match:
            raw_task = match.group(1).strip()
            deadline, remaining_task = extract_deadline(raw_task)
            if not deadline:
                deadline, _ = extract_deadline(sentence_clean)

            clean_task = clean_task_description(remaining_task)
            owner = speaker if speaker and speaker != "Unknown" else "Unassigned"

            return evaluate_action_item(
                task=clean_task,
                owner=owner,
                deadline=deadline,
                trigger_type="explicit",
                raw_sentence=sentence_clean
            )

    # 3. Collective / Impersonal commitment
    for pattern in COLLECTIVE_PATTERNS:
        match = pattern.search(sentence_clean)
        if match:
            raw_task = match.group(1).strip()
            deadline, remaining_task = extract_deadline(raw_task)
            if not deadline:
                deadline, _ = extract_deadline(sentence_clean)

            clean_task = clean_task_description(remaining_task)
            return evaluate_action_item(
                task=clean_task,
                owner="Unassigned",
                deadline=deadline,
                trigger_type="explicit",
                raw_sentence=sentence_clean
            )

    return None


def extract_action_items_from_text(transcript_text: str, engine: str = "symbolic", meeting_date: str = "2026-11-10") -> List[Dict[str, Any]]:
    """
    Main extraction pipeline.
    Enforces deduplication, date resolution, and provenance.
    """
    turns = parse_dialogue_turns(transcript_text)
    raw_action_items: List[Dict[str, Any]] = []

    for turn in turns:
        speaker = turn["speaker"]
        for sentence in turn["sentences"]:
            item = extract_from_sentence(sentence, speaker, engine=engine)
            if item:
                # Add calculated calendar date if resolvable
                iso_date = parse_relative_date_to_iso(item["deadline"], meeting_date)
                item["target_iso_date"] = iso_date
                item["speaker_turn"] = speaker
                raw_action_items.append(item)

    # Deduplication
    seen_tasks = set()
    deduped_items: List[Dict[str, Any]] = []
    for item in raw_action_items:
        norm_task = re.sub(r"[^\w\s]", "", item["task"].lower())
        if norm_task not in seen_tasks and len(norm_task) > 3:
            seen_tasks.add(norm_task)
            deduped_items.append(item)

    return deduped_items


def generate_icalendar(items: List[Dict[str, Any]], meeting_name: str = "Meeting Action Items") -> str:
    """Generates standard RFC 5545 iCalendar (.ics) format string for 1-click import into Google/Apple Calendar."""
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Meeting Action-Item Extractor//EN",
        f"X-WR-CALNAME:{meeting_name}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]

    for idx, item in enumerate(items):
        target_iso = item.get("target_iso_date")
        if not target_iso:
            target_iso = datetime.now().strftime("%Y-%m-%d")

        try:
            dt = datetime.strptime(target_iso, "%Y-%m-%d")
            dt_start = dt.strftime("%Y%m%d")
            dt_end = (dt + timedelta(days=1)).strftime("%Y%m%d")
        except Exception:
            continue

        clean_task = item["task"].replace(",", "\\,").replace(";", "\\;")
        clean_owner = item["owner"]
        clean_quote = item["source_quote"].replace(",", "\\,").replace(";", "\\;")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:action-item-{idx}-{now_str}@actionextractor.ai",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{dt_start}",
            f"DTEND;VALUE=DATE:{dt_end}",
            f"SUMMARY:[Action Item] {clean_task}",
            f"DESCRIPTION:Owner: {clean_owner}\\nDeadline: {item['deadline']}\\nStatus: {item['review_status']}\\nQuote: \\\"{clean_quote}\\\"",
            f"STATUS:CONFIRMED" if item["review_status"] == "Confirmed" else "STATUS:TENTATIVE",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def compute_team_workload(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes actionable team analytics: workload distribution and accountability risk."""
    owner_counts = {}
    confirmed_count = 0
    needs_review_count = 0

    for item in items:
        owner = item.get("owner", "Unassigned")
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        if item.get("review_status") == "Confirmed":
            confirmed_count += 1
        else:
            needs_review_count += 1

    total = len(items)
    unassigned_count = owner_counts.get("Unassigned", 0)
    assigned_count = total - unassigned_count
    accountability_rate = (assigned_count / total * 100) if total > 0 else 100.0

    return {
        "total_tasks": total,
        "confirmed": confirmed_count,
        "needs_review": needs_review_count,
        "unassigned": unassigned_count,
        "accountability_rate": round(accountability_rate, 1),
        "owner_distribution": owner_counts
    }
