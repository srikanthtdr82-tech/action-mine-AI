"""
test_extractor.py
Automated test suite verifying the extraction rules and the No-Guessing constraint.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractor import extract_action_items_from_text
from src.evaluator import evaluate_predictions


def test_sample_1_mobile_app_sync():
    """Verifies that Carlos is confirmed, Priya is unassigned, and Marcus lacks deadline."""
    transcript = (
        "[00:01] Carlos: Good morning everyone! Did everyone catch the football match yesterday evening?\n"
        "[00:02] Priya: Haha, yes Carlos, incredible game! But we should probably look at our release blockers.\n"
        "[00:03] Carlos: Right, down to business. I will update the API authentication documentation by tomorrow at 3 PM.\n"
        "[00:04] Priya: Great. Also, we really need to redesign the user onboarding illustrations before the marketing push next Friday.\n"
        "[00:05] Marcus: I can help coordinate the user testing sessions, but I haven't checked my calendar yet so I'm not sure when.\n"
        "[00:06] Carlos: Sounds like a plan. Let's reconvene on Wednesday."
    )
    items = extract_action_items_from_text(transcript)
    assert len(items) == 3, f"Expected 3 action items, got {len(items)}"

    # Item 1: Carlos
    carlos_item = next(i for i in items if i["owner"] == "Carlos")
    assert "update the api authentication documentation" in carlos_item["task"].lower()
    assert "tomorrow at 3 pm" in carlos_item["deadline"].lower()
    assert carlos_item["confidence"] == "High"
    assert carlos_item["review_status"] == "Confirmed"

    # Item 2: Unassigned owner (Priya said "we really need to")
    unassigned_item = next(i for i in items if i["owner"] == "Unassigned")
    assert "redesign" in unassigned_item["task"].lower()
    assert "next friday" in unassigned_item["deadline"].lower()
    assert unassigned_item["review_status"] == "Needs review"

    # Item 3: Marcus with unspecified deadline
    marcus_item = next(i for i in items if i["owner"] == "Marcus")
    assert "user testing" in marcus_item["task"].lower()
    assert marcus_item["deadline"] == "Unspecified"
    assert marcus_item["review_status"] == "Needs review"


def test_sample_3_zero_action_items():
    """Verifies that conversational chatter and vague brainstorming yields zero action items."""
    chatter = (
        "Maya: That was a great presentation. We could potentially explore entering the European market next year, "
        "but honestly, sales were already strong in Asia last quarter. What do you think?\n"
        "Liam: I agree, let's keep that in mind for future discussions."
    )
    items = extract_action_items_from_text(chatter)
    assert len(items) == 0, f"Expected 0 action items from chatter, got {len(items)}"


def test_no_guessing_safety_guarantee():
    """Verifies that incomplete items are NEVER flagged as Confirmed."""
    incomplete_utterance = "Someone needs to push the hotfix to the staging server before 8 PM tonight."
    items = extract_action_items_from_text(incomplete_utterance)
    assert len(items) == 1
    item = items[0]
    assert item["owner"] == "Unassigned"
    # STRICT SAFETY ASSERTION:
    assert item["review_status"] == "Needs review", "Safety violation: unassigned item marked Confirmed!"


if __name__ == "__main__":
    test_sample_1_mobile_app_sync()
    test_sample_3_zero_action_items()
    test_no_guessing_safety_guarantee()
    print("All extraction and safety tests passed successfully!")
