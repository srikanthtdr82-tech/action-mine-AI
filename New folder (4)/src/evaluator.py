"""
evaluator.py
Computes quantitative evaluation metrics: Precision, Recall, F1-Score,
Owner Accuracy, Deadline Accuracy, Review Trigger Rate, and False-Certainty Rate.
"""

from typing import List, Dict, Any


def compute_similarity(str1: str, str2: str) -> float:
    """Computes simple word-overlap Jaccard similarity between two strings."""
    tokens1 = set(str1.lower().split())
    tokens2 = set(str2.lower().split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def evaluate_predictions(gold_items: List[Dict[str, Any]], pred_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compares gold-standard action items with predicted action items.
    
    A predicted item is considered a True Positive if its task has Jaccard similarity >= 0.4
    with an unmatched gold item.
    """
    matched_gold_indices = set()
    true_positives = 0
    correct_owners = 0
    correct_deadlines = 0
    false_certainties = 0  # CRITICAL: Items with missing details marked as Confirmed!

    for pred in pred_items:
        best_match_idx = None
        best_sim = 0.0
        
        for idx, gold in enumerate(gold_items):
            if idx in matched_gold_indices:
                continue
            sim = compute_similarity(pred["task"], gold["task"])
            if sim > best_sim:
                best_sim = sim
                best_match_idx = idx

        if best_match_idx is not None and best_sim >= 0.35:
            # Match found: True positive
            true_positives += 1
            matched_gold_indices.add(best_match_idx)
            gold_item = gold_items[best_match_idx]

            # Check owner match
            gold_owner = (gold_item.get("owner") or "Unassigned").strip().lower()
            pred_owner = (pred.get("owner") or "Unassigned").strip().lower()
            if gold_owner in pred_owner or pred_owner in gold_owner:
                correct_owners += 1

            # Check deadline match
            gold_deadline = (gold_item.get("deadline") or "Unspecified").strip().lower()
            pred_deadline = (pred.get("deadline") or "Unspecified").strip().lower()
            if (gold_deadline == "unspecified" and pred_deadline == "unspecified") or (gold_deadline in pred_deadline or pred_deadline in gold_deadline):
                correct_deadlines += 1

        # Check safety rule: If an item is missing owner or deadline, it MUST NOT be Confirmed!
        is_missing_details = pred.get("owner") == "Unassigned" or pred.get("deadline") == "Unspecified"
        if is_missing_details and pred.get("review_status") == "Confirmed":
            false_certainties += 1

    false_positives = len(pred_items) - true_positives
    false_negatives = len(gold_items) - true_positives

    precision = true_positives / len(pred_items) if pred_items else (1.0 if not gold_items else 0.0)
    recall = true_positives / len(gold_items) if gold_items else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    owner_acc = correct_owners / true_positives if true_positives > 0 else 1.0
    deadline_acc = correct_deadlines / true_positives if true_positives > 0 else 1.0

    review_count = sum(1 for p in pred_items if p.get("review_status") == "Needs review")
    review_rate = review_count / len(pred_items) if pred_items else 0.0
    false_certainty_rate = false_certainties / len(pred_items) if pred_items else 0.0

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "owner_accuracy": round(owner_acc, 3),
        "deadline_accuracy": round(deadline_acc, 3),
        "total_extracted": len(pred_items),
        "items_needing_review": review_count,
        "review_rate": round(review_rate, 3),
        "false_certainty_rate": round(false_certainty_rate, 3)
    }
