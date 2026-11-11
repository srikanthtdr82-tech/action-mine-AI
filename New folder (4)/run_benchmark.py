"""
run_benchmark.py
Runs the extraction pipeline across all sample transcripts in data/sample_transcripts.json
and prints quantitative evaluation metrics.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractor import extract_action_items_from_text
from src.evaluator import evaluate_predictions


def main():
    data_path = PROJECT_ROOT / "data" / "sample_transcripts.json"
    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    all_gold = []
    all_pred = []

    print("\n" + "="*60)
    print("  AI MEETING ACTION-ITEM EXTRACTOR: BENCHMARK SUITE")
    print("="*60)

    for sample in samples:
        print(f"\nEvaluating: {sample['title']}...")
        predicted = extract_action_items_from_text(sample["transcript"])
        gold = sample["expected_action_items"]

        metrics = evaluate_predictions(gold, predicted)
        print(f"  Extracted: {metrics['total_extracted']} | Expected: {len(gold)}")
        print(f"  Precision: {metrics['precision']:.2f} | Recall: {metrics['recall']:.2f} | F1: {metrics['f1_score']:.2f}")
        print(f"  Needs Review: {metrics['items_needing_review']} ({metrics['review_rate']*100:.0f}%) | False-Certainty Rate: {metrics['false_certainty_rate']*100:.1f}%")

        all_gold.extend(gold)
        all_pred.extend(predicted)

    total_metrics = evaluate_predictions(all_gold, all_pred)
    print("\n" + "-"*60)
    print("  AGGREGATE BENCHMARK PERFORMANCE")
    print("-" * 60)
    print(f"  Total Action Items Extracted: {total_metrics['total_extracted']}")
    print(f"  Overall Precision:            {total_metrics['precision']*100:.1f}%")
    print(f"  Overall Recall:               {total_metrics['recall']*100:.1f}%")
    print(f"  Overall F1-Score:             {total_metrics['f1_score']:.3f}")
    print(f"  Owner Assignment Accuracy:    {total_metrics['owner_accuracy']*100:.1f}%")
    print(f"  Deadline Detection Accuracy:  {total_metrics['deadline_accuracy']*100:.1f}%")
    print(f"  Human Review Trigger Rate:    {total_metrics['review_rate']*100:.1f}%")
    print(f"  False-Certainty Rate (Safety):{total_metrics['false_certainty_rate']*100:.1f}% (Must be 0.0%)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
