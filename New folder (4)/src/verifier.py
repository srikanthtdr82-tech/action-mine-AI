"""
verifier.py
Enforces the strict "No-Guessing" rule and computes transparent confidence scores.
"""

from typing import Dict, Any, List

GENERIC_OWNERS = {
    "someone", "we", "everybody", "everyone", "team", "somebody",
    "anybody", "anyone", "us", "all", "unknown", "unassigned", "nobody"
}

VAGUE_DEADLINES = {
    "soon", "later", "someday", "eventually", "at some point",
    "whenever", "unspecified", "tbd", "asap", "down the road"
}

HEDGING_KEYWORDS = {
    "maybe", "perhaps", "might consider", "could potentially",
    "think about", "look into possibly", "wondering if"
}


def evaluate_action_item(
    task: str,
    owner: str | None,
    deadline: str | None,
    trigger_type: str = "explicit",
    raw_sentence: str = ""
) -> Dict[str, Any]:
    """
    Evaluates an extracted action item strictly against the No-Guessing Rule.
    
    If owner or deadline is missing, vague, or guessed, it is normalized to 
    'Unassigned' or 'Unspecified' and marked as 'Needs review'.
    """
    review_reasons: List[str] = []
    
    # 1. Evaluate Owner
    clean_owner = (owner or "").strip()
    if not clean_owner or clean_owner.lower() in GENERIC_OWNERS:
        final_owner = "Unassigned"
        review_reasons.append("Missing or unassigned owner (collective/vague reference)")
    else:
        final_owner = clean_owner

    # 2. Evaluate Deadline
    clean_deadline = (deadline or "").strip()
    if not clean_deadline or clean_deadline.lower() in VAGUE_DEADLINES:
        final_deadline = "Unspecified"
        review_reasons.append("Missing explicit deadline or date constraint")
    else:
        final_deadline = clean_deadline

    # 3. Evaluate Task Description & Hedging
    clean_task = (task or "").strip()
    # Clean leading punctuation or junk
    clean_task = clean_task.lstrip(":- ,;.")
    if len(clean_task.split()) < 2:
        review_reasons.append("Task description is very short or fragmented")

    raw_lower = raw_sentence.lower()
    for hedge in HEDGING_KEYWORDS:
        if hedge in raw_lower:
            review_reasons.append(f"Contains hedging or uncertain language ('{hedge}')")
            break

    # 4. Determine Confidence & Review Status
    # High Confidence: Explicit commitment trigger, explicit owner, explicit deadline, no hedging
    # Medium Confidence: Valid task, but missing either owner OR deadline
    # Low Confidence: Missing BOTH owner and deadline, OR contains hedging keywords
    
    missing_critical_count = 0
    if final_owner == "Unassigned":
        missing_critical_count += 1
    if final_deadline == "Unspecified":
        missing_critical_count += 1

    has_hedging = any("hedging" in r for r in review_reasons)

    if missing_critical_count == 0 and not has_hedging and trigger_type == "explicit":
        confidence = "High"
        review_status = "Confirmed"
        reason_summary = "Fully specified commitment with explicit owner and deadline."
    elif missing_critical_count <= 1 and not has_hedging:
        confidence = "Medium"
        review_status = "Needs review"
        reason_summary = "; ".join(review_reasons)
    else:
        confidence = "Low"
        review_status = "Needs review"
        reason_summary = "; ".join(review_reasons)

    return {
        "task": clean_task,
        "owner": final_owner,
        "deadline": final_deadline,
        "confidence": confidence,
        "review_status": review_status,
        "review_reason": reason_summary,
        "source_quote": raw_sentence.strip()
    }
